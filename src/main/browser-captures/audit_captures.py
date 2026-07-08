#!/usr/bin/env python
"""
audit_captures.py — list known/suspect problems across the browser-captures corpus.

The recapture workflow needs a staleness detector: after having (or extending) a
conversation, the user recaptures it in place (Shortcut / --id); this tool says which
captures need attention. Two independent questions, two modes:

Filesystem audit (always) — "are the captures I have any good?"
  claude — every scrape .md is checked against the api projection (project_markdown
  output) with compare_markdown's turn-sequence classifier; any regression kind marks
  the scrape suspect. Captures without a scrape .md are fine (the scrape is optional;
  the api JSON is the primary artifact) and counted informationally.
  gemini — no api side exists, so heuristics: a scrape with exactly RENDER_CEILING
  human turns is flagged as likely truncated (the pre-walking-scraper window), and
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
  src/run_python_script.sh src/main/browser-captures/audit_captures.py \
    [--browser-captures ext/browser-captures] [--api lib/markdown/claude/conversations] [--live]

Exit status is non-zero iff anything actionable is found.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import turn_seq, conv_id  # the format authority owns the parsers
from compare_markdown import classify

# Gemini renders only the last N exchanges until scrolled; a scrape sitting exactly
# at the ceiling is overwhelmingly likely to be a truncated pre-walking-scraper one.
RENDER_CEILING = 10


def audit_claude(captures_dir: Path, api_dir: Path) -> list[str]:
    suspects = []
    api_md = {}
    for f in api_dir.glob('*.md'):
        text = f.read_text()
        cid = conv_id(text)
        if cid:
            api_md[cid] = text
    unscraped = unprojected = 0
    for d in sorted(captures_dir.iterdir()):
        mds = sorted(d.glob('*.md')) if d.is_dir() else []
        if not mds:
            unscraped += 1
            continue
        s = mds[0].read_text()
        cid = conv_id(s) or d.name
        if cid not in api_md:
            unprojected += 1
            continue
        kind, _ = classify(turn_seq(s), turn_seq(api_md[cid]))
        if kind not in ('exact', 'improved'):
            suspects.append((d.name, mds[0].stem, kind))
    # One WARN per disagreeing scrape, its recapture command beside it; counts
    # that are zero say nothing, and optional-by-design facts are plain lines.
    for uuid, stem, kind in suspects:
        print(f'WARN: claude .md scrape {uuid} ({stem}) disagrees with its api json — {kind}. '
              "claude's scrape is retired (the api json is the record): delete the scrape .md, "
              'or refresh it:')
        print(f'    → run: src/main/browser-captures/safari_capture.sh --agent claude --scrape --id {uuid}'
              f'  # first front https://claude.ai/chat/{uuid} in Safari (logged in); the scrape walk takes minutes')
    if unscraped:
        print(f'claude: {unscraped} capture dir(s) have no scrape .md — optional; the api json is the record')
    if unprojected:
        print(f'WARN: claude: {unprojected} scrape(s) have no rendered api markdown under lib/markdown — '
              'the browser-captures pipeline step project_markdown produces it')
    # show the working even on success: silence was load-bearing here once —
    # a clean audit and a skipped one printed identically (nothing)
    checked = sum(1 for d in sorted(captures_dir.iterdir()) if d.is_dir() and list(d.glob('*.md')))
    print(f'claude: {checked} scrape(s) checked against api projections — '
          + ('all aligned' if not suspects else f'{len(suspects)} suspect(s), WARNed above'))
    return [f'{u} ({s}): {k}' for u, s, k in suspects]


def audit_gemini(captures_dir: Path) -> list[str]:
    suspects = []
    placeholder_convs = 0
    for d in sorted(captures_dir.iterdir()):
        mds = sorted(d.glob('*.md')) if d.is_dir() else []
        if not mds:
            continue
        s = mds[0].read_text()
        humans = sum(1 for r, _ in turn_seq(s) if r == 'H')
        if humans == RENDER_CEILING:
            suspects.append((d.name, mds[0].stem))
        if '[no capture' in s:
            placeholder_convs += 1
    for cid, stem in suspects:
        print(f'WARN: gemini scrape {cid} ({stem}) shows exactly {RENDER_CEILING} human turns — '
              f'the gemini page renders only the last {RENDER_CEILING}, so earlier turns are '
              'likely missing from this scrape; to recapture:')
        print(f'    → run: src/main/browser-captures/safari_capture.sh --agent gemini --id {cid}'
              '  # a full scrape walks the page — takes a couple of minutes')
    if placeholder_convs:
        print(f'gemini: {placeholder_convs} scrape(s) contain "[no capture" placeholder text')
    checked = sum(1 for d in sorted(captures_dir.iterdir()) if d.is_dir() and list(d.glob('*.md')))
    print(f'gemini: {checked} scrape(s) health-checked (no api side exists — heuristics only) — '
          + ('nothing flagged' if not suspects else f'{len(suspects)} suspect(s), WARNed above'))
    return [f'{c} ({s})' for c, s in suspects]


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

    actionable = []
    for uuid, updated in sorted(listing.items()):
        if uuid not in captured:
            actionable.append(f'NEW {uuid}: never captured')
        elif updated > captured[uuid]:
            actionable.append(f'PROGRESSED {uuid}: captured {captured[uuid]} < updated {updated}')
    unlisted = sorted(set(captured) - set(listing))
    print(f'claude live: {len(listing)} conversations listed; '
          f'{sum(1 for a in actionable if a.startswith("NEW"))} new, '
          f'{sum(1 for a in actionable if a.startswith("PROGRESSED"))} progressed, '
          f'{len(unlisted)} captured-but-no-longer-listed (deleted/archived?)')
    return actionable


def live_gemini(captures_dir: Path) -> list[str]:
    """Browse the listing for NEW ids; tail-check each captured conversation
    (append-only: an unchanged rendered tail means an unchanged conversation)."""
    from safari_capture import AGENTS, ids_from_safari, wait_for_ready
    from safari_utils import safari_navigate, safari_eval_js, PAGE_LOAD_WAIT
    cfg = AGENTS['gemini']
    ids = ids_from_safari(cfg)
    captured_dirs = {d.name: d for d in captures_dir.iterdir() if d.is_dir()}

    actionable = [f'NEW {i}: never captured' for i in ids if i not in captured_dirs]
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
            actionable.append(f'PROGRESSED {cid} ({mds[0].stem}): rendered tail no longer '
                              f'matches the captured last turns')
    unlisted = sorted(set(captured_dirs) - set(ids))
    print(f'gemini live: {len(ids)} conversations listed; '
          f'{sum(1 for a in actionable if a.startswith("NEW"))} new, '
          f'{sum(1 for a in actionable if a.startswith("PROGRESSED"))} progressed '
          f'(tail-checked {checked}), {len(unlisted)} captured-but-no-longer-listed')
    return actionable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', default='ext/browser-captures',
                    help='captures root containing claude/ and gemini/')
    ap.add_argument('--api', default='lib/markdown/claude/conversations',
                    help='dir of api-sourced markdown (project_markdown output)')
    ap.add_argument('--live', action='store_true',
                    help='also drive Safari (work tab): claude listing updated_at check; '
                         'gemini listing + rendered-tail checks')
    args = ap.parse_args()

    root = Path(args.browser_captures)
    api_dir = Path(args.api)
    suspects = []

    claude_dir = root / 'claude'
    if claude_dir.is_dir() and api_dir.is_dir():
        suspects += audit_claude(claude_dir, api_dir)
    else:
        print(f'claude: skipped ({claude_dir} or {api_dir} absent)')

    gemini_dir = root / 'gemini'
    if gemini_dir.is_dir():
        suspects += audit_gemini(gemini_dir)
    else:
        print(f'gemini: skipped ({gemini_dir} absent)')

    actionable = []
    if args.live:
        from safari_utils import safari_open_work_tab, safari_close_work_tab
        prev_tab = safari_open_work_tab()
        try:
            if claude_dir.is_dir():
                actionable += live_claude(claude_dir)
            if gemini_dir.is_dir():
                actionable += live_gemini(gemini_dir)
        finally:
            safari_close_work_tab(prev_tab)
        for a in actionable:
            print(f'  {a}')

    return 1 if (suspects or actionable) else 0


if __name__ == '__main__':
    sys.exit(main())
