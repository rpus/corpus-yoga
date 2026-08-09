#!/usr/bin/env python
"""
audit_captures.py — list known/suspect problems across the browser-captures corpus.

The recapture workflow needs a staleness detector: after having (or extending) a
conversation, the user recaptures it (Shortcut / --id); this tool says which
captures need attention. Two independent questions, two modes:

Filesystem audit (always) — "are the captures I have any good?"
  claude — every DOM capture is checked against the projection of the API capture
  (project_markdown output) with compare_markdown's turn-sequence classifier; any
  regression kind marks the DOM capture suspect. A conversation with no DOM capture is
  fine (DOM is optional for claude; the API capture is the record) and counted
  informationally.
  gemini — no API capture exists, so heuristics: a DOM capture with exactly
  RENDER_CEILING human turns is flagged as likely truncated (the pre-walking window), and
  '[no capture' placeholders are counted informationally.

--live (drives Safari, in a work tab) — "which conversations have moved on?"
  claude — ONE authenticated listing fetch returns every conversation's updated_at;
  compared against each captured JSON's updated_at: NEW (never captured) and
  PROGRESSED (updated since capture).
  gemini — the listing is browsed for NEW ids; then each captured conversation is
  visited and its immediately-rendered TAIL (conversations are append-only, so an
  unchanged tail means an unchanged conversation) is compared against the capture's
  last agent turn, alphanumeric-normalized so markdown-vs-rendered differences wash
  out. Mismatch = PROGRESSED (rendering edge cases err toward recapture, e.g. a
  response ending in rendered maths).

Usage:
  src/run_python_script.sh src/main/pipeline/browser-captures/audit_captures.py \
    [--input input] [--api data/output/markdown/claude/chat/conversations] [--live]

Exit status is non-zero iff anything actionable is found.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

SELF = 'src/main/pipeline/browser-captures/audit_captures.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))  # src/main/ on the path
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'browser'))  # the acquisition machinery --live reaches (#380)
sys.path.insert(0, str(REPO / 'src' / 'main' / 'pipeline' / 'chat-exports'))  # library.py — the artifact library's owner (#421)
from markdown_projection import turn_seq, conv_id, turn_extent  # the format authority owns the parsers
from compare_markdown import classify, turn_labels
from safari_utils import SendRefused   # --live sends; the refusal has to be catchable here

# Gemini renders only the last N exchanges until scrolled; a DOM capture sitting exactly
# at the ceiling is overwhelmingly likely to be a truncated pre-walking one.
RENDER_CEILING = 10


def _attribute(kind: str, evidence: list, capture: Path) -> str:
    """Re-word a projection-side shortfall once the API capture has been consulted:
    absent from the record is `API capture missing N`; present in it is a rendering
    difference, which is not a loss and should not read like one."""
    if not capture.is_file():
        return kind + ' (API capture not on this machine — cause unattributed)'
    try:
        blob = json.loads(capture.read_text())
    except Exception:
        return kind + ' (API capture unreadable — cause unattributed)'
    record = ' '.join(re.sub(r'\s+', ' ', c.get('text', ''))
                      for m in blob.get('chat_messages', [])
                      for c in (m.get('content') or []) if isinstance(c, dict))
    absent = [body for _, body in evidence if body[:60].strip() and body[:60] not in record]
    n = len(evidence)
    if not absent:
        return (f'projection renders {n} turn(s) differently — the content IS in the API '
                f'capture, so nothing is missing from the record')
    return f'API capture missing {len(absent)} of {n} turn(s)' if len(absent) < n \
        else f'API capture missing {n} turn(s)'


def audit_claude(dom_dir: Path, api_capture_dir: Path, api_dir: Path) -> list[str]:
    """Scrapes live under browser-DOM/, api json under browser-API/ — the
    conversation id is the join. An API capture with no DOM capture is found by that
    join, not by an empty dir: the DOM root only holds ids that were captured."""
    suspects = []
    # The projection's FILENAME is the humane identity — data/output/markdown names every
    # conversation <NNN>-<title>.md, stable and sortable. Keeping only the text threw that
    # away and left the WARN citing a 36-char uuid and a slug with the ordinal stripped:
    # the machine half kept, the human half mangled, when the file carried both.
    projected = {}
    for f in api_dir.glob('*.md'):
        text = f.read_text()
        cid = conv_id(text)
        if cid:
            projected[cid] = (text, f.stem)
    unprojected = 0
    have_dom = set()
    for d in sorted(dom_dir.iterdir()) if dom_dir.is_dir() else []:
        mds = sorted(d.glob('*.md')) if d.is_dir() else []
        if not mds:
            continue
        have_dom.add(d.name)
        s = mds[0].read_text()
        cid = conv_id(s) or d.name
        if cid not in projected:
            unprojected += 1
            continue
        text, name = projected[cid]
        kind, detail, evidence = classify(turn_seq(s), turn_seq(text),
                                          turn_labels(s), turn_labels(text))
        if kind.startswith('projection missing') and evidence:
            # The comparison is markdown vs markdown and cannot tell a turn the RECORD
            # lacks from a turn project_markdown rendered differently. We hold the record,
            # so we ask it — the difference decides whether this is content loss or a
            # rendering artifact, which want opposite responses from a reader.
            kind = _attribute(kind, evidence, api_capture_dir / d.name / f'{d.name}.json')
        if kind not in ('exact', 'improved'):
            # `detail` names the turns that differ — discarded, it leaves the reader
            # with a count and no way to judge it without re-running the comparison
            suspects.append((d.name, name, kind, detail))
    # One WARN per disagreeing DOM capture, naming the conversation the way the corpus
    # does (<NNN>-<title>, uuid8 beside it) and the turns that differ. Both sides compared
    # are MARKDOWN — the projection of the API capture, and the DOM capture — so the
    # difference may belong to project_markdown's rendering rather than to either capture,
    # and the WARN says so instead of prescribing a re-capture as though it could not.
    # The record first. Attribution decides severity and order: content absent from the API
    # capture is the only kind that means anything is LOST — the others are a retired
    # mechanism lagging, or a rendering difference over a record that is intact.
    suspects.sort(key=lambda x: (not x[2].startswith('API capture missing'), x[1]))
    if suspects:
        # said ONCE, not per WARN: it is the same fact about the comparison every time,
        # and three copies of a paragraph is how a report teaches its reader to skim.
        print('claude: the comparison is markdown vs markdown — the projection of the API '
              'capture against the DOM capture — so a difference may be in project_markdown '
              "rather than in either capture. claude's DOM capture is retired; the API "
              'capture is the record.')
    for uuid, name, kind, detail in suspects:
        # identity leads, on its own line; the finding and its remedy are the body, aligned
        # (pipeline.sh's hoist_atoms carries an atom's indented continuation).
        #
        # Severity follows the ATTRIBUTION, and the test is: was anything LOST? For claude
        # the API capture is the record and the DOM capture is retired, so a DOM capture
        # that lags leaves the corpus complete — INFO, like a rendering difference. WARN is
        # left meaning one thing only: content absent from the record. That the WARN class
        # is presently EMPTY is itself the report — a fact this output could not state while
        # every difference was a warning.
        lost = kind.startswith('API capture missing')
        intact = kind.startswith('projection renders')
        print(f'{"WARN" if lost else "INFO"}: {name} ({uuid[:8]}):')
        print(f'    {kind}' + (f' — {detail}' if detail else ''))
        if intact:
            print('    nothing to re-capture: the record holds the content. The DOM capture '
                  'is retired — delete it to retire the difference with it.')
        else:
            # a lagging DOM capture is not a loss, but re-capturing IS the action if you
            # want it current — so the remedy stays, at INFO
            # claude's DOM is retired (#418): the one remedy is deletion — no
            # advice line may name a retired mechanism as a thing to run.
            print('    delete its DOM capture — the record (the API capture) holds the conversation')
    unscraped = sum(1 for d in api_capture_dir.iterdir()
                    if d.is_dir() and d.name not in have_dom) if api_capture_dir.is_dir() else 0
    if unscraped:
        print(f'claude: {unscraped} API capture(s) have no DOM capture — '
              'optional; the API capture is the record')
    if unprojected:
        print(f'WARN: claude: {unprojected} DOM capture(s) have no projection under data/output/markdown — '
              'the browser-captures pipeline step project_markdown produces it')
    # show the working even on success: silence was load-bearing here once —
    # a clean audit and a skipped one printed identically (nothing)
    checked = len(have_dom)
    print(f'claude: {checked} DOM capture(s) checked against their projections — '
          + ('all aligned' if not suspects else f'{len(suspects)} suspect(s), WARNed above'))
    return [f'{name} ({uuid[:8]}): {kind}' for uuid, name, kind, _ in suspects]


def audit_gemini(captures_dir: Path, projection_dir: Path | None = None) -> list[str]:
    # gemini has no API capture, so the DOM capture IS the record — but its projection
    # is numbered like every other conversation, so the WARN can still name it the way
    # the corpus does rather than by uuid alone.
    projected, projected_text = {}, {}
    for f in (projection_dir.glob('*.md') if projection_dir and projection_dir.is_dir() else []):
        text = f.read_text()
        cid = conv_id(text)
        if cid:
            projected[cid] = f.stem
            projected_text[cid] = text
    suspects = []
    placeholder_convs = 0
    for d in sorted(captures_dir.iterdir()):
        mds = sorted(d.glob('*.md')) if d.is_dir() else []
        if not mds:
            continue
        s = mds[0].read_text()
        humans = sum(1 for r, _ in turn_seq(s) if r == 'H')
        if humans == RENDER_CEILING:
            suspects.append((d.name, projected.get(conv_id(s) or d.name, mds[0].stem)))
        if '[no capture' in s:
            placeholder_convs += 1
    for cid, name in suspects:
        print(f'WARN: {name} ({cid[:8]}): shows exactly {RENDER_CEILING} human turns — '
              f'the gemini page renders only the last {RENDER_CEILING}, so earlier turns are '
              'likely missing from this DOM capture; to recapture:')
        print(f'    → run: yoga browser capture --provider gemini --id {cid}'
              '  # walks the page — takes a couple of minutes')
    if placeholder_convs:
        print(f'gemini: {placeholder_convs} DOM capture(s) contain "[no capture" placeholder text')
    # The capture against the rendering derived FROM it. gemini has no API, so nothing
    # else corroborates either one -- and `yoga pipeline run` rewrites the projection from
    # the capture every time, so a divergence means the two have already parted company.
    # The capture is a copy plus turn anchors, so they must agree turn for turn.
    if projected_text:
        for d in sorted(captures_dir.iterdir()):
            mds = sorted(d.glob('*.md')) if d.is_dir() else []
            if not mds:
                continue
            text = mds[0].read_text()
            cid = conv_id(text) or d.name
            if cid not in projected_text:
                print(f'WARN: {mds[0].stem} ({cid[:8]}): captured but not projected — '
                      f'the gemini step of `yoga pipeline run` produces it')
                suspects.append((cid, mds[0].stem))
                continue
            cap, proj = turn_seq(text), turn_seq(projected_text[cid])
            if len(cap) != len(proj):
                print(f'WARN: {projected[cid]} ({cid[:8]}): capture holds {len(cap)} turns, '
                      f'its projection {len(proj)} — the projection is derived from the '
                      f'capture, so they cannot legitimately differ')
                suspects.append((cid, projected[cid]))
            elif any(a != b for a, b in zip(cap, proj)):
                first = next(i for i, (a, b) in enumerate(zip(cap, proj)) if a != b)
                print(f'WARN: {projected[cid]} ({cid[:8]}): capture and projection differ '
                      f'from turn {first + 1} of {len(cap)} — the projection is derived from '
                      f'the capture, so they cannot legitimately differ')
                suspects.append((cid, projected[cid]))
        unprojected = sorted(set(projected_text) -
                             {conv_id(sorted(d.glob('*.md'))[0].read_text()) or d.name
                              for d in captures_dir.iterdir()
                              if d.is_dir() and list(d.glob('*.md'))})
        for cid in unprojected:
            print(f'WARN: {projected[cid]} ({cid[:8]}): projected but no capture remains — '
                  f'the rendering has outlived the record it was derived from')
            suspects.append((cid, projected[cid]))

    checked = sum(1 for d in sorted(captures_dir.iterdir()) if d.is_dir() and list(d.glob('*.md')))
    print(f'gemini: {checked} DOM capture(s) checked against their projections '
          f'(no API capture exists, so nothing corroborates the record itself) — '
          + ('nothing flagged' if not suspects else f'{len(suspects)} suspect(s), WARNed above'))
    return [f'{n} ({c[:8]})' for c, n in suspects]


def _alnum(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())


CLAUDE_LISTING_JS = """(async function() {
  window.__audit = '';
  const orgId = document.cookie.match(/lastActiveOrg=([^;]+)/)?.[1];
  if (!orgId) { window.__audit = 'ERROR: no lastActiveOrg cookie — not logged in?'; return; }
  const r = await fetch('/api/organizations/' + orgId + '/chat_conversations?limit=10000',
                        {credentials: 'include'});
  if (!r.ok) { window.__audit = 'ERROR: HTTP ' + r.status; return; }
  const d = await r.json();
  const arr = Array.isArray(d) ? d : (d.data || d.chat_conversations || []);
  window.__audit = JSON.stringify(arr.map(c => [c.uuid, c.updated_at]));
})();"""

# NB: no // comments in eval'd JS — safari_eval_js flattens newlines to spaces, so a
# line comment would swallow the rest of the function. Each part is sliced SEPARATELY:
# a long final response must not evict the human tail from the returned blob.
GEMINI_TAIL_JS = """(function(){
  var uq = document.querySelectorAll('user-query');
  var mr = document.querySelectorAll('model-response');
  var u = uq.length ? (uq[uq.length - 1].innerText || '') : '';
  var m = mr.length ? (mr[mr.length - 1].innerText || '') : '';
  return (u.replace(/\\s+/g, ' ').slice(-600) + ' | ' + m.replace(/\\s+/g, ' ').slice(-600));
})()"""


def report_live(provider: str, findings: list[tuple[str, str, str]]) -> list[str]:
    """Print each finding under the provider that produced it, with the command that acts
    on it — never a bare id in a list that has left its provider behind. Returns the
    findings for the caller's exit status."""
    for kind, cid, detail in findings:
        print(f'  {provider} {kind} {cid}: {detail}')
        print(f'    → run: yoga browser capture --provider {provider} --id {cid}')
    return [f'{provider} {kind} {cid}' for kind, cid, _ in findings]


def live_claude(captures_dir: Path) -> list[str]:
    """One listing fetch: every conversation's updated_at vs the captured JSONs'."""
    from safari_utils import safari_navigate, safari_eval_js, PAGE_LOAD_WAIT
    safari_navigate('https://claude.ai/recents')
    time.sleep(PAGE_LOAD_WAIT + 2)
    safari_eval_js(CLAUDE_LISTING_JS)
    raw = ''
    for _ in range(30):
        raw = safari_eval_js('window.__audit || ""')
        if raw:
            break
        time.sleep(0.5)
    if not raw or raw.startswith('ERROR'):
        print(f'claude live: listing fetch failed ({raw or "timeout"})')
        return []
    listing = dict(json.loads(raw))

    captured = {}
    for d in sorted(captures_dir.iterdir()):
        j = d / f'{d.name}.json' if d.is_dir() else None
        if j and j.exists():
            captured[d.name] = json.load(j.open()).get('updated_at', '')

    found = []
    for uuid, updated in sorted(listing.items()):
        if uuid not in captured:
            found.append(('NEW', uuid, 'never captured'))
        elif updated > captured[uuid]:
            found.append(('PROGRESSED', uuid, f'captured {captured[uuid]} < updated {updated}'))
    unlisted = sorted(set(captured) - set(listing))
    print(f'claude live: {len(listing)} conversations listed; '
          f'{sum(1 for k, _, _ in found if k == "NEW")} new, '
          f'{sum(1 for k, _, _ in found if k == "PROGRESSED")} progressed, '
          f'{len(unlisted)} captured-but-no-longer-listed (deleted/archived?)')
    return report_live('claude', found)


def live_gemini(captures_dir: Path) -> list[str]:
    """Browse the listing for NEW ids; tail-check each captured conversation
    (append-only: an unchanged rendered tail means an unchanged conversation)."""
    from safari_capture import PROVIDERS, ids_from_safari, wait_for_ready
    from safari_utils import safari_navigate, safari_eval_js, PAGE_LOAD_WAIT
    cfg = PROVIDERS['gemini']
    ids = ids_from_safari('gemini', cfg)
    captured_dirs = {d.name: d for d in captures_dir.iterdir() if d.is_dir()}

    found = [('NEW', i, 'never captured') for i in ids if i not in captured_dirs]
    checked = 0
    for cid in (i for i in ids if i in captured_dirs):
        mds = sorted(captured_dirs[cid].glob('*.md'))
        if not mds:
            continue
        seq = turn_seq(mds[0].read_text())
        # Two probes, either match = current. The HUMAN probe is the robust one (typed
        # text renders literally); the agent probe can false-mismatch when a response
        # ends in rendered maths/markup, whose glyphs alnum-normalize away.
        probes = []
        for role in ('H', 'A'):
            turns = [b for r, b in seq if r == role]
            if turns:
                probes.append(_alnum(turns[-1])[-120:])
        probes = [p for p in probes if p]
        if not probes:
            continue
        safari_navigate(cfg['chat_url'].format(id=cid))
        time.sleep(PAGE_LOAD_WAIT)
        wait_for_ready(cfg['ready_sel'])
        checked += 1
        page = _alnum(safari_eval_js(GEMINI_TAIL_JS))
        if not any(p in page for p in probes):
            found.append(('PROGRESSED', cid, f'"{mds[0].stem}" — rendered tail no longer '
                                             f'matches the captured last turns'))
    unlisted = sorted(set(captured_dirs) - set(ids))
    print(f'gemini live: {len(ids)} conversations listed; '
          f'{sum(1 for k, _, _ in found if k == "NEW")} new, '
          f'{sum(1 for k, _, _ in found if k == "PROGRESSED")} progressed '
          f'(tail-checked {checked}), {len(unlisted)} captured-but-no-longer-listed')
    return report_live('gemini', found)


def main():
    # The one thing an unmigrated machine needs this face to say (#421): the
    # library's stated move — bare `yoga browser` is where a tester looks first.
    from library import migration_note
    migration_note()
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='input',
                    help='input root, typed <provider>/<channel>/<capture> — the audit '
                         'derives claude/chat/browser-{API,DOM} and gemini/chat/browser-DOM')
    ap.add_argument('--api', default='data/output/markdown/claude/chat/conversations',
                    help='dir of api-sourced markdown (project_markdown output)')
    ap.add_argument('--live', action='store_true',
                    help='also drive Safari (work tab): claude listing updated_at check; '
                         'gemini listing + rendered-tail checks')
    ap.add_argument('--provider', choices=['claude', 'gemini'], default=None,
                    help='restrict to one provider (default: every provider). The live pass '
                         'costs wildly different amounts per provider — claude is one listing '
                         'fetch, gemini navigates to every captured conversation in turn — so '
                         'which to pay for is the reader\'s to choose')
    args = ap.parse_args()

    root = Path(args.input)
    api_dir = Path(args.api)
    claude_api = root / 'claude' / 'chat' / 'browser-API'
    claude_dom = root / 'claude' / 'chat' / 'browser-DOM'
    gemini_dom = root / 'gemini' / 'chat' / 'browser-DOM'
    suspects = []

    # one restriction, applied wherever the audit is partitioned by provider — the
    # offline pass included, so `--provider claude` means the same thing throughout
    def want(provider):
        return args.provider in (None, provider)

    if want('claude'):
        if claude_api.is_dir() and api_dir.is_dir():
            suspects += audit_claude(claude_dom, claude_api, api_dir)
        else:
            print(f'claude: skipped ({claude_api} or {api_dir} absent)')

    if want('gemini') and gemini_dom.is_dir():
        # every provider's projection sits under the one corpus root, so gemini's is
        # named from it rather than guessed: --api gives claude's, three levels down
        corpus_root = Path(args.api).parents[2]
        suspects += audit_gemini(gemini_dom, corpus_root / 'gemini' / 'chat' / 'conversations')
    elif want('gemini'):
        print(f'gemini: skipped ({gemini_dom} absent)')

    actionable = []
    if args.live:
        from safari_utils import safari_open_work_tab, safari_close_work_tab
        prev_tab = safari_open_work_tab()
        try:
            # each pass prints its own findings as it completes them, so no id ever
            # appears in a list that has left the provider which produced it behind
            if claude_api.is_dir() and want('claude'):
                actionable += live_claude(claude_api)
            if gemini_dom.is_dir() and want('gemini'):
                actionable += live_gemini(gemini_dom)
        finally:
            safari_close_work_tab(prev_tab)

    return 1 if (suspects or actionable) else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SendRefused as e:
        # --live is a send; the filesystem audit is not. Exit 3 says refused, not "failed".
        print(e, file=sys.stderr)
        sys.exit(3)
