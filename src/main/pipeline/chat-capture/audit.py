#!/usr/bin/env python
"""
audit.py — list known/suspect problems across the chat-capture corpus.

The recapture workflow needs a staleness detector: after having (or extending) a
conversation, the user recaptures it (Shortcut / --id); this tool says which
captures need attention. Two independent questions, two modes:

Filesystem audit (always) — "are the captures I have any good?"
  claude — nothing to check offline: the API capture is the record (DOM retired,
  #418/#431), and validate.sh already gates each capture against the schema.
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
  src/run_python_script.sh src/main/pipeline/chat-capture/audit.py \
    [--input input] [--api data/output/markdown/claude/chat/conversations] [--live]

Exit status is non-zero iff anything actionable is found.
"""
import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/pipeline/chat-capture/audit.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))  # src/main/ on the path
import tier  # noqa: E402 — the tiers, one home (#702)
import facts  # noqa: E402 - the one printer of a status's facts (#753)
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'browser'))  # the acquisition machinery --live reaches (#380)
sys.path.insert(0, str(REPO / 'src' / 'main' / 'pipeline' / 'chat-export'))  # library.py — the artifact library's owner (#421)
from markdown_projection import turn_seq, conv_id  # the format authority owns the parsers
from safari import SendRefused   # --live sends; the refusal has to be catchable here

# Gemini renders only the last N exchanges until scrolled; a DOM capture sitting exactly
# at the ceiling is overwhelmingly likely to be a truncated pre-walking one.
RENDER_CEILING = 10


@dataclass
class Claude:
    offline_check: str
    live: str


@dataclass
class Gemini:
    """The offline findings on gemini's DOM captures: each a FAIL under the conversation it names."""
    checked: int = facts.named('DOM captures checked against their projections')
    corroboration: str = 'none - no API capture exists, so nothing corroborates the record itself'
    placeholders: int | None = facts.named('with "[no capture" placeholder text', default=None)
    findings: dict[str, facts.Finding] | str = 'nothing flagged'


@dataclass
class Moved:
    """A conversation the live pass found new or progressed, with the capture that acts on it."""
    standing: str
    remedy: facts.Command


@dataclass
class Live:
    """One provider's live pass: the account's listing against the captures."""
    conversations_listed: int
    new: int
    progressed: int
    captured_but_no_longer_listed: int
    tail_checked: int | None = facts.named('tail-checked', default=None)
    findings: dict[str, Moved] | str = 'none'   # by conversation


@dataclass
class Audit:
    """The capture audit: each provider's offline standing, and its live pass where one ran."""
    claude: Claude | None = None
    gemini: Gemini | str | None = None
    claude_live: Live | str | None = None
    gemini_live: Live | str | None = None


def audit_gemini(captures_dir: Path, projection_dir: Path | None = None) -> tuple[Gemini, list[str]]:
    """The offline findings on gemini's DOM captures (#753, #759), and the suspects' names."""
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
    findings: dict[str, facts.Finding] = {}
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
        findings[f'{name} ({cid[:8]})'] = facts.Finding(
            f'shows exactly {RENDER_CEILING} human turns - the gemini page renders only the last '
            f'{RENDER_CEILING}, so earlier turns are likely missing from this DOM capture',
            facts.Command(f'corpus-yoga browser capture --provider gemini --id {cid}', 'walks the page, a couple of minutes'))
    # The capture against the rendering derived FROM it. gemini has no API, so nothing
    # else corroborates either one -- and `corpus-yoga pipeline run` rewrites the projection from
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
                findings[f'{mds[0].stem} ({cid[:8]})'] = facts.Finding(
                    'captured but not projected', facts.Command('corpus-yoga pipeline run', 'its gemini step produces it'))
                suspects.append((cid, mds[0].stem))
                continue
            cap, proj = turn_seq(text), turn_seq(projected_text[cid])
            if len(cap) != len(proj):
                findings[f'{projected[cid]} ({cid[:8]})'] = facts.Finding(
                    f'capture holds {len(cap)} turns, its projection {len(proj)} - the projection is '
                    'derived from the capture, so they cannot legitimately differ')
                suspects.append((cid, projected[cid]))
            elif any(a != b for a, b in zip(cap, proj)):
                first = next(i for i, (a, b) in enumerate(zip(cap, proj)) if a != b)
                findings[f'{projected[cid]} ({cid[:8]})'] = facts.Finding(
                    f'capture and projection differ from turn {first + 1} of {len(cap)} - the projection '
                    'is derived from the capture, so they cannot legitimately differ')
                suspects.append((cid, projected[cid]))
        unprojected = sorted(set(projected_text) -
                             {conv_id(sorted(d.glob('*.md'))[0].read_text()) or d.name
                              for d in captures_dir.iterdir()
                              if d.is_dir() and list(d.glob('*.md'))})
        for cid in unprojected:
            findings[f'{projected[cid]} ({cid[:8]})'] = facts.Finding(
                'projected but no capture remains - the rendering has outlived the record it was derived from')
            suspects.append((cid, projected[cid]))

    checked = sum(1 for d in sorted(captures_dir.iterdir()) if d.is_dir() and list(d.glob('*.md')))
    return (Gemini(checked, placeholders=placeholder_convs or None, findings=findings or 'nothing flagged'),
            [f'{n} ({c[:8]})' for c, n in suspects])


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


def moved(provider: str, findings: list[tuple[str, str, str]]) -> dict[str, Moved] | str:
    """Each live finding under the conversation it names, with the command that acts on it -
    never a bare id in a list that has left its provider behind."""
    return {cid: Moved(f'{kind} - {detail}', facts.Command(f'corpus-yoga browser capture --provider {provider} --id {cid}', 'recaptures it'))
            for kind, cid, detail in findings} or 'none'


def live_claude(captures_dir: Path) -> tuple[Live | str, list[str]]:
    """One listing fetch: every conversation's updated_at vs the captured JSONs'."""
    from safari import safari_navigate, safari_eval_js, PAGE_LOAD_WAIT
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
        return f'listing fetch failed ({raw or "timeout"})', []
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
    return (Live(len(listing), sum(1 for k, _, _ in found if k == 'NEW'), sum(1 for k, _, _ in found if k == 'PROGRESSED'),
                 len(unlisted), findings=moved('claude', found)),
            [f'claude {kind} {cid}' for kind, cid, _ in found])


def live_gemini(captures_dir: Path) -> tuple[Live | str, list[str]]:
    """Browse the listing for NEW ids; tail-check each captured conversation
    (append-only: an unchanged rendered tail means an unchanged conversation)."""
    from capture import PROVIDERS, ids_from_safari, wait_for_ready
    from safari import safari_navigate, safari_eval_js, PAGE_LOAD_WAIT
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
    return (Live(len(ids), sum(1 for k, _, _ in found if k == 'NEW'), sum(1 for k, _, _ in found if k == 'PROGRESSED'),
                 len(unlisted), tail_checked=checked, findings=moved('gemini', found)),
            [f'gemini {kind} {cid}' for kind, cid, _ in found])


def main():
    # The one thing an unmigrated machine needs this face to say (#421): the
    # library's stated move — bare `corpus-yoga browser` is where a tester looks first.
    from library import migration_note
    migration_note()
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='input',
                    help='input root, typed <provider>/<channel>/<capture> — the audit '
                         'derives claude/chat/API-capture and gemini/chat/DOM-capture')
    ap.add_argument('--api', default=str(tier.DATA / 'output' / 'markdown' / 'claude' / 'chat' / 'conversations'),
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

    shape, found = audit(Path(args.input), Path(args.api), args.provider, args.live)
    facts.say(shape)
    return 1 if found else 0


def audit(root: Path, api: Path, provider: str | None = None, live: bool = False) -> tuple[Audit, bool]:
    """The audit as its shape, and whether anything actionable was found: the offline pass
    over the captures under root, and with live the account's listing against them."""
    claude_api = root / 'claude' / 'chat' / 'API-capture'
    gemini_dom = root / 'gemini' / 'chat' / 'DOM-capture'
    suspects: list[str] = []
    out = Audit()

    # one restriction, applied wherever the audit is partitioned by provider — the
    # offline pass included, so `--provider claude` means the same thing throughout
    def want(name):
        return provider in (None, name)

    if want('claude'):
        # the absence is the report: with DOM retired there is no second render to
        # reconcile the record against, and schema validation already ran per capture
        out.claude = Claude('none - the API capture is the record (DOM retired)', '--live compares it against the account')

    if want('gemini') and gemini_dom.is_dir():
        # every provider's projection sits under the one corpus root, so gemini's is
        # named from it rather than guessed: api gives claude's, three levels down
        corpus_root = api.parents[2]
        out.gemini, suspects = audit_gemini(gemini_dom, corpus_root / 'gemini' / 'chat' / 'conversations')
    elif want('gemini'):
        shown = gemini_dom.relative_to(REPO) if gemini_dom.is_relative_to(REPO) else gemini_dom
        out.gemini = f'skipped - {shown} absent'

    actionable: list[str] = []
    if live:
        from safari import safari_open_work_tab, safari_close_work_tab
        prev_tab = safari_open_work_tab()
        try:
            if claude_api.is_dir() and want('claude'):
                out.claude_live, moved_ = live_claude(claude_api)
                actionable += moved_
            if gemini_dom.is_dir() and want('gemini'):
                out.gemini_live, moved_ = live_gemini(gemini_dom)
                actionable += moved_
        finally:
            safari_close_work_tab(prev_tab)

    return out, bool(suspects or actionable)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SendRefused as e:
        # --live is a send; the filesystem audit is not. Exit 3 says refused, not "failed".
        print(e, file=sys.stderr)
        sys.exit(3)
