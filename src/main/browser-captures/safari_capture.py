#!/usr/bin/env python
"""
safari_capture.py — Capture conversations from claude.ai or gemini.google.com via Safari.

One script, dispatched on --agent. Each agent declares what it can capture:
  claude : api=True  (fetch the apiConversation JSON — the reliable source), scrape opt-in
  gemini : api=False, scrape=True (no API; the DOM scrape is the only source)
--scrape additionally runs the DOM scrape for an api agent (Claude), saving markdown alongside the
JSON so compare_markdown can check the projection against it. Claude's scrape is otherwise retired
(slow, brittle, redundant — markdown is derived from the JSON by project_markdown).

Discovery (the conversation-id listing) is shared: navigate to the agent's listing URL and scroll.

Two orthogonal behaviours, selected by targeting (the invoker — CLI, PREP.sh, or the
macOS Shortcut — is independent of the mode):
  (no args)   Discover every conversation from the listing, then navigate through and
              capture all of them — in a dedicated work tab; the user's front tab is
              restored afterwards.
  --id <id>   Capture ONE conversation. If the front tab already shows it, capture
              in place (no navigation — the capture-what-you're-reading workflow);
              otherwise navigate to it in a work tab, like discovery mode for one id.

Requires Safari open, focused, and logged into the site throughout.
Called by safari_capture.sh — do not invoke directly.

Usage:
    python safari_capture.py --agent claude            --browser-captures input/browser-captures/claude
    python safari_capture.py --agent claude --scrape   --browser-captures input/browser-captures/claude
    python safari_capture.py --agent gemini --id <id>  --browser-captures input/browser-captures/gemini
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from safari_utils import (  # type: ignore[import-not-found]
    osascript, safari_focus, safari_navigate, safari_run_js_file, safari_eval_js,
    safari_open_work_tab, safari_close_work_tab,
    safari_fetch_api_json, collect_md_and_log, process_chain,
    PAGE_LOAD_WAIT,
)

REPO_DIR       = Path(__file__).resolve().parents[3]
SCRIPT_DIR     = Path(__file__).resolve().parent
SETTLE_PAUSE   = 2
READY_TIMEOUT  = 15   # max wait for a conversation to render / its URL to commit, before capturing
SCRAPE_START_TIMEOUT = 5    # the scrape JS must signal window.__scrape within this, else it never ran
SCRAPE_STALL_TIMEOUT = 20   # max time with no newly-captured message before giving up on a scrape
SCROLL_PAUSE   = 2    # wait between scroll-to-bottom ticks while loading the conversation list
SCROLL_STABLE  = 3    # consecutive no-growth ticks before the list is deemed fully loaded
MAX_SCROLLS    = 80   # safety cap on scroll iterations


AGENTS = {
    'claude': {
        'api':          True,
        'scrape':       False,   # opt-in via --scrape; otherwise api-only
        'chat_url':     'https://claude.ai/chat/{id}',
        'discover_url': 'https://claude.ai/recents',
        'link_sel':     'a[href*="/chat/"]',
        'id_re':        None,
        'ready_sel':    'button[data-testid="action-bar-copy"]',
    },
    'gemini': {
        'api':          False,
        'scrape':       True,
        'chat_url':     'https://gemini.google.com/app/{id}',
        'discover_url': 'https://gemini.google.com/app',
        'link_sel':     'a[href*="/app/"]',
        'id_re':        r'^[0-9a-f]{8,}$',
        'ready_sel':    'button[aria-label="Copy"]',
        # the DOM scrapes carry no timestamps, so the listing order is the one
        # ordering observation there is — persisted as ordering.txt on every
        # discovery sweep (claude needs none: created_at is its authority)
        'ordering_capture': True,
    },
}


def write_ordering(cfg, ids, captures_root):
    """Persist the discovery listing as the ordering CAPTURE, ordering.txt —
    gemini only (cfg['ordering_capture']): the web-UI lists newest-first by
    edit time, reversed here to ascending so line N is conversation N,
    paralleling claude's created_at ordinals. Refreshed on every discovery
    sweep; a --id capture observes no listing and leaves it untouched.
    Consumed by copy_gemini_markdown for NN- naming."""
    if not cfg.get('ordering_capture') or not ids:
        return
    out = captures_root / 'ordering.txt'
    header = (
        '# gemini conversation ordering — a CAPTURE of the web-UI listing (gemini.google.com/app),\n'
        '# reversed to ascending: the UI lists newest-first by edit time, so line N here is\n'
        "# conversation N, paralleling claude's created_at ordinals. Ordinals are presentation\n"
        '# and renumber as the corpus changes (an edit resurfaces a conversation; a new one\n'
        '# appends); the id is the identity. Refreshed by every discovery sweep\n'
        '# (safari_capture ids_from_safari → write_ordering); consumed by\n'
        '# copy_gemini_markdown for NN- naming.\n'
        f'# Captured {time.strftime("%Y-%m-%d")}.\n'
    )
    out.write_text(header + '\n'.join(reversed(ids)) + '\n')
    print(f'ordering: {len(ids)} conversation(s) → {out}')


def outcome(do_api, do_scrape, files, had_md):
    """Per-conversation success/failure. The apiConversation JSON is the reliable artifact; when
    both are captured a missing scrape .md is only a note. For a scrape-only agent (Gemini) a
    missing .md is the failure."""
    has_json = any(f.endswith('.json') for f in files)
    has_md = any(f.endswith('.md') for f in files)
    if do_api and not has_json:
        return 'apiConversation JSON fetch failed — the FAIL: line above carries the remedy', None
    if do_scrape and not has_md:
        why = 'no markdown — see the scrape log under logs/.../safari_capture/<agent>/scrape/'
        if had_md:
            why += ' (previous .md retained, now STALE)'
        return (None, why) if do_api else (why, None)
    return None, None


def discover_js(cfg):
    """Build the conversation-id discovery snippet for this agent's link selector / id filter."""
    sel = cfg['link_sel']
    test = f'/{cfg["id_re"]}/.test(id) && ' if cfg['id_re'] else ''
    return (
        "(function(){var seen=new Set(),r=[];"
        "document.querySelectorAll('" + sel + "').forEach(function(a){"
        "var id=a.pathname.split('/').pop();"
        "if(id && " + test + "!seen.has(id)){seen.add(id);r.push(id);}"
        "});return r.join('\\n');})()"
    )


def wait_for_ready(selector, timeout=READY_TIMEOUT):
    """Poll until the conversation has rendered (>=1 `selector`, e.g. a copy button) or timeout --
    so slow (citation/LaTeX-heavy) conversations aren't scraped before their DOM exists."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if int(safari_eval_js(f"String(document.querySelectorAll('{selector}').length)") or 0) > 0:
                return True
        except (ValueError, TypeError):
            pass
        time.sleep(0.5)
    return False


def wait_for_url(conv_id, timeout=READY_TIMEOUT):
    """Wait until the front tab's URL is this conversation, so the API fetch reads the right uuid
    from window.location."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if (safari_eval_js('location.pathname') or '').rstrip('/').endswith(conv_id):
            return True
        time.sleep(0.3)
    return False


def fetch_api(conv_id, out_dir):
    """Fetch the apiConversation JSON; returns the saved filename, or None on failure."""
    f = safari_fetch_api_json(conv_id)
    if f is None:
        return None
    try:
        shutil.move(str(f), out_dir / f'{conv_id}.json')
    except PermissionError:
        # macOS TCC: reading ~/Downloads needs a per-app grant held by some app
        # in this process's ancestry — print the ancestry so the reader knows
        # which app to grant (Files and Folders only lists apps that have
        # ASKED; Full Disk Access accepts manual additions via its + button).
        print(f'FAIL: macOS denied reading {f} from this process chain:\n'
              f'    {process_chain()}\n'
              '    grant the outermost app Downloads access (System Settings → Privacy & '
              'Security; Full Disk Access takes manual additions where Files and Folders '
              f'shows nothing). The fetched json is stranded in ~/Downloads — move it '
              f'into {out_dir} by hand, or recapture from an already-granted Terminal:\n'
              f'    → run: src/main/browser-captures/safari_capture.sh --agent claude '
              f'--id {conv_id}  # first front https://claude.ai/chat/{conv_id} in Safari',
              file=sys.stderr)
        return None
    return f'{conv_id}.json'


def scrape_state():
    """Read the in-page scrape liveness/progress flag (window.__scrape), or None if not set yet."""
    raw = safari_eval_js('JSON.stringify(window.__scrape || null)')
    if not raw or raw == 'null':
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def scrape_one(out_dir, js_script, log_dir):
    """Inject the DOM scraper and WATCH its in-page flag rather than waiting out a timeout: abort
    fast if it never starts (page wedged) or stalls (no new message), finish the moment it signals
    done. Returns the collected md filenames, or None if the scrape produced no markdown."""
    start = time.time()
    safari_run_js_file(js_script)
    print('  scrape injected, watching...')
    last_n, last_change = -1, time.time()
    while True:
        st = scrape_state()
        now = time.time()
        if st is None:
            if now - start > SCRAPE_START_TIMEOUT:
                print('  scrape never started (page wedged?) — skipping')
                return None
        elif st.get('done'):
            if st.get('error'):
                print(f"  scrape failed: {st['error']}")
            break
        else:
            # progress is a heartbeat that ticks every scroll step: on virtualized pages the
            # walk-to-top phase captures nothing for minutes, but is not a stall.
            n = st.get('captured', 0) + st.get('progress', 0)
            if n != last_n:
                last_n, last_change = n, now
            elif now - last_change > SCRAPE_STALL_TIMEOUT:
                print(f'  scrape stalled at {st.get("captured", 0)} message(s) — skipping')
                return None
        time.sleep(0.5)
    time.sleep(SETTLE_PAUSE)   # let the .md/.log downloads land
    return collect_md_and_log(start, out_dir, log_dir)


def ids_from_safari(cfg):
    safari_focus()
    print(f'navigating to {cfg["discover_url"]}')
    safari_navigate(cfg['discover_url'])
    time.sleep(PAGE_LOAD_WAIT)
    print('loading all conversations...')
    sel = cfg['link_sel']
    prev = stable = 0
    for _ in range(MAX_SCROLLS):
        safari_eval_js(
            "(function(){"
            "var a=document.querySelector('" + sel + "');"
            "while(a){var s=getComputedStyle(a);"
            'if((s.overflowY==="scroll"||s.overflowY==="auto")&&a.scrollHeight>a.clientHeight)'
            "{a.scrollTo(0,a.scrollHeight);return;}"
            "a=a.parentElement;}"
            "window.scrollTo(0,document.body.scrollHeight);"
            "})()"
        )
        time.sleep(SCROLL_PAUSE)
        try:
            count = int(safari_eval_js("String(document.querySelectorAll('" + sel + "').length)"))
        except (ValueError, TypeError):
            break
        # only conclude the list is fully loaded after SCROLL_STABLE consecutive no-growth ticks --
        # a single slow lazy-load tick must NOT end the scroll (that dropped the older tail before)
        stable = stable + 1 if count == prev else 0
        if stable >= SCROLL_STABLE:
            break
        prev = count
    else:
        print(f'  hit MAX_SCROLLS ({MAX_SCROLLS}) — list may be longer than discovered', file=sys.stderr)
    print('extracting conversation IDs')
    raw = safari_eval_js(discover_js(cfg))
    ids = [u for u in raw.splitlines() if u]
    print(f'found {len(ids)} conversations')
    return ids


def capture_all(agent, ids, captures_root, navigate=True, also_scrape=False):
    cfg = AGENTS[agent]
    do_api = cfg['api']
    do_scrape = cfg['scrape'] or also_scrape
    js_script = SCRIPT_DIR / agent / 'browser-chat-capture.js'
    # per-conversation scrape diagnostics go under logs/ (input/ holds captured data only)
    scrape_log_dir = REPO_DIR / 'logs' / 'src' / 'main' / 'browser-captures' / 'safari_capture' / agent / 'scrape'
    label = 'discover' if navigate else 'capture'
    methods = '+'.join(m for m, on in (('api', do_api), ('scrape', do_scrape)) if on)
    if not ids:
        print(f'{label}: nothing to do')
        return []
    print(f'--- {label} started {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    print(f'capturing {len(ids)} conversations ({methods})')
    safari_focus()
    failed = []
    for i, conv_id in enumerate(ids):
        print(f'[{i+1}/{len(ids)}] {conv_id}')
        out_dir = captures_root / conv_id
        out_dir.mkdir(parents=True, exist_ok=True)
        had_md = any(out_dir.glob('*.md'))
        if navigate:
            safari_navigate(cfg['chat_url'].format(id=conv_id))
        start = time.time()
        files = []
        if do_api:
            if navigate:
                wait_for_url(conv_id)
                time.sleep(SETTLE_PAUSE)
            j = fetch_api(conv_id, out_dir)
            if j:
                files.append(j)
        if do_scrape:
            if navigate:
                wait_for_url(conv_id)   # confirm the NEW conversation loaded, not a stale/transitioning page
                if not wait_for_ready(cfg['ready_sel']):
                    print(f'  not rendered after {READY_TIMEOUT}s — scraping anyway (likely to fail)')
            safari_eval_js(f'window.__capture_progress = "{i + 1}/{len(ids)}"')  # in-page "conversation i/N"
            files += scrape_one(out_dir, js_script, scrape_log_dir) or []
        print(f'  done in {time.time() - start:.0f}s — {", ".join(files) or "(no files)"}')
        fatal, note = outcome(do_api, do_scrape, files, had_md)
        if note:
            print(f'  note: {note}', file=sys.stderr)
        if fatal:
            failed.append((conv_id, fatal))
    print(f'--- {label} finished {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    if failed:
        print(f'\n⚠ {len(failed)}/{len(ids)} failed:', file=sys.stderr)
        for cid, why in failed:
            print(f'    {cid}: {why}', file=sys.stderr)
        if len(ids) > 1:
            # a sweep's bulk remedy, beside the per-item ones above: fix the
            # cause the FAIL lines name, then re-sweep (runnable, full path —
            # a bare 'PREP.sh' names four different scripts in this repo)
            print('    → run: src/main/browser-captures/PREP.sh'
                  '  # re-sweep after fixing the cause(s) the FAIL lines above name',
                  file=sys.stderr)
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agent', required=True, choices=['claude', 'gemini'])
    ap.add_argument('--browser-captures', default=None,
                    help='Path to input/browser-captures/<agent>/ (default: repo-relative)')
    ap.add_argument('--id', metavar='ID',
                    help='Capture ONE conversation — in place if the front tab shows it, '
                         'else navigated to in a work tab; default is to discover and capture all')
    ap.add_argument('--scrape', action='store_true',
                    help='also run the DOM scrape (Claude; feeds compare_markdown). No effect for Gemini.')
    args = ap.parse_args()

    cfg = AGENTS[args.agent]
    if cfg['scrape'] or args.scrape:
        js_script = SCRIPT_DIR / args.agent / 'browser-chat-capture.js'
        if not js_script.exists():
            print(f'Error: {js_script} not found', file=sys.stderr)
            raise SystemExit(1)

    captures_root = Path(args.browser_captures or REPO_DIR / 'input' / 'browser-captures' / args.agent).resolve()
    captures_root.mkdir(parents=True, exist_ok=True)

    if args.id:
        # Single capture. If the front tab already shows the conversation, capture it in
        # place (the capture-what-you're-reading workflow: no navigation, browser untouched);
        # otherwise do exactly what discovery mode does for one id — navigate in a dedicated
        # work tab and restore the front tab — so the audit's remedy runs as printed. Either
        # way the id is verified against the page before filing (wait_for_url on the
        # navigating path), never trusted.
        front_url = osascript('tell application "Safari" to get URL of front document')
        if args.id in front_url:
            failed = capture_all(args.agent, [args.id], captures_root, navigate=False, also_scrape=args.scrape)
        else:
            prev_tab = safari_open_work_tab()
            try:
                failed = capture_all(args.agent, [args.id], captures_root,
                                     navigate=True, also_scrape=args.scrape)
            finally:
                safari_close_work_tab(prev_tab)
    else:
        # Discovery mode navigates through every conversation — do that in a dedicated
        # work tab so the user's front tab survives, and restore it afterwards.
        prev_tab = safari_open_work_tab()
        try:
            ids = ids_from_safari(cfg)
            write_ordering(cfg, ids, captures_root)
            failed = capture_all(args.agent, ids, captures_root,
                                 navigate=True, also_scrape=args.scrape)
        finally:
            safari_close_work_tab(prev_tab)
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
