#!/usr/bin/env python
"""
safari_capture.py — Capture conversations from claude.ai or gemini.google.com via Safari.

Scope is two independent restrictions, and the run is their intersection:
  --provider  <p>   claude | gemini      (default: every provider)
  --mechanism API|DOM                    (default: every mechanism the provider has)
Neither adds. A provider has the mechanisms PROVIDERS declares — claude API and DOM,
gemini DOM — and a restriction can only take mechanisms away. Asking for one a
provider lacks selects nothing, which is reported rather than substituted for.

Each mechanism deposits under its own root — the capture axis of the corpus type
system (data/input/<provider>/<channel>/<capture>/):
  browser-API : data/input/<provider>/chat/browser-API/<id>/<id>.json
  browser-DOM : data/input/<provider>/chat/browser-DOM/<id>/<title>.md  (+ gemini's ordering.txt)
The same conversation id names the capture dir under both roots — the id is the join.
Claude's DOM capture is also what compare_markdown checks the projection against.

Discovery (the conversation-id listing) is shared: navigate to the provider's listing URL and scroll.

Two orthogonal behaviours, selected by targeting (the invoker — CLI, browser.sh, or the
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
    python safari_capture.py --provider claude                   [--browser-api  data/input/claude/chat/browser-API]
    python safari_capture.py --provider claude --mechanism DOM   [--browser-dom  data/input/claude/chat/browser-DOM]
    python safari_capture.py --provider gemini --id <id>         [--browser-dom  data/input/gemini/chat/browser-DOM]
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from safari_utils import (  # type: ignore[import-not-found]
    osascript, safari_focus, safari_navigate, safari_run_js_file, safari_eval_js,
    safari_open_work_tab, safari_close_work_tab,
    safari_fetch_api_json, collect_md_and_log, process_chain,
    SendRefused,
    PAGE_LOAD_WAIT,
)

SELF = 'src/main/cli/browser/safari_capture.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_DIR = _root[0]
SCRIPT_DIR     = Path(__file__).resolve().parent

# ── channels (#413): the run log carries the narrative, the terminal the anchor,
# one line per conversation, and the verdict. TERM is the real terminal; when
# --run-log is given, sys.stdout becomes the log (line-buffered — nothing sits
# in a buffer a ctrl-C could erase, #415) and sys.stderr writes to both.
TERM = sys.stdout


def emit(line=''):
    """A terminal-altitude line: printed to the terminal, recorded in the log
    (they are the same stream until --run-log splits them)."""
    print(line)
    if TERM is not sys.stdout:
        print(line, file=TERM, flush=True)


class _BothStreams:
    """stderr under --run-log: failures belong on the terminal AND in the record."""
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
        self.flush()

    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except OSError:
                pass


def rel(path):
    """The repo-relative spelling of a path where one exists (#412): logs speak
    the repo's addresses, never a resolved machine path."""
    try:
        return str(Path(path).resolve().relative_to(REPO_DIR))
    except ValueError:
        return str(path)


# The run's own tally, written by capture_all and read by the footer — including
# the interrupted footer, which must say how far the run got (#415).
RUN = {'t0': None, 'total': 0, 'done': 0, 'failed': [], 'at': '', 'log': None}


def anchor(provider, mechanisms, conv_id):
    """The log's first words (#412): stamp, room, commit, invocation — written
    before any work, so a wordless log is impossible."""
    binding = REPO_DIR / 'machine-name.txt'
    room = binding.read_text().strip() if binding.exists() else '(unbound room)'
    head = subprocess.run(['git', '-C', str(REPO_DIR), 'rev-parse', '--short', 'HEAD'],
                          capture_output=True, text=True).stdout.strip() or '(no commit)'
    dirty = bool(subprocess.run(['git', '-C', str(REPO_DIR), 'status', '--porcelain'],
                                capture_output=True, text=True).stdout.strip())
    stamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    what = f'--provider {provider} --mechanism {"+".join(mechanisms)}' + (f' --id {conv_id}' if conv_id else '')
    emit(f'{stamp} · {room} · {head}{" (dirty)" if dirty else ""}')
    emit(f'yoga browser capture {what}')


def footer(interrupted=False):
    """The run's last words, on both channels: captured N of M, the failures by
    id with their reasons, wall-clock. A ctrl-C is a verdict, not an eraser."""
    dt = time.time() - RUN['t0'] if RUN['t0'] else 0
    verdict = 'INTERRUPTED (ctrl-C)' if interrupted else 'done'
    at = f' at {RUN["at"]}' if interrupted and RUN['at'] else ''
    emit(f'--- {verdict}{at}: {RUN["done"]}/{RUN["total"]} captured, '
         f'{len(RUN["failed"])} failed · {dt:.0f}s ---')
    for cid, why in RUN['failed']:
        emit(f'    {cid}: {why}')
SETTLE_PAUSE   = 2
READY_TIMEOUT  = 15   # first wait for a render; the caller retries 4x longer (see wait_for_ready)
SCRAPE_START_TIMEOUT = 5    # the scrape JS must signal window.__scrape within this, else it never ran
SCRAPE_STALL_TIMEOUT = 20   # max time with no newly-captured message before giving up on a scrape
SCROLL_PAUSE   = 2    # wait between scroll-to-bottom ticks while loading the conversation list
SCROLL_STABLE  = 3    # consecutive no-growth ticks before the list is deemed fully loaded
MAX_SCROLLS    = 80   # safety cap on scroll iterations


# What each provider HAS, and nothing about what runs. These two must not be
# conflated: a mechanism listed here can be asked for, and asking is a restriction
# (--mechanism), never an addition. The axis is the corpus's own — the third path
# component of data/input/<provider>/chat/browser-{API,DOM}/ — so the values here
# are the values on disk.
PROVIDERS = {
    'claude': {
        'mechanisms':   ('API', 'DOM'),
        'chat_url':     'https://claude.ai/chat/{id}',
        'discover_url': 'https://claude.ai/recents',
        'link_sel':     'a[href*="/chat/"]',
        'id_re':        None,
        'ready_sel':    'button[data-testid="action-bar-copy"]',
    },
    'gemini': {
        'mechanisms':   ('DOM',),
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


def write_ordering(cfg, ids, dom_root):
    """Persist the discovery listing as the ordering CAPTURE, ordering.txt —
    gemini only (cfg['ordering_capture']): the web-UI lists newest-first by
    edit time, reversed here to ascending so line N is conversation N,
    paralleling claude's created_at ordinals. Refreshed on every discovery
    sweep; a --id capture observes no listing and leaves it untouched.
    Consumed by copy_gemini_markdown for NN- naming."""
    if not cfg.get('ordering_capture') or not ids:
        return
    out = dom_root / 'ordering.txt'
    header = (
        '# gemini conversation ordering — a CAPTURE of the web-UI listing (gemini.google.com/app),\n'
        '# reversed to ascending: the UI lists newest-first by edit time, so line N here is\n'
        "# conversation N, paralleling claude's created_at ordinals. Ordinals are presentation\n"
        '# and renumber as the corpus changes (an edit resurfaces a conversation; a new one\n'
        '# appends); the id is the identity. Refreshed by every discovery sweep\n'
        '# (safari_capture ids_from_safari → write_ordering); consumed by\n'
        '# copy_gemini_markdown for NN- naming.\n'
        # Provenance, not a clock-label: the run log holds the sweep this listing
        # came from, and its stamped name carries the when.
        + (f'# Captured by yoga browser capture — run log: {rel(RUN["log"])}\n'
           if RUN['log'] else '# Captured by safari_capture.py (no run log named).\n')
    )
    out.write_text(header + '\n'.join(reversed(ids)) + '\n')
    print(f'ordering: {len(ids)} conversation(s) → {rel(out)}')


def outcome(do_api, do_scrape, files, had_md):
    """Per-conversation success/failure. The apiConversation JSON is the reliable artifact; when
    both are captured a missing scrape .md is only a note. For a DOM-only provider (Gemini) a
    missing .md is the failure."""
    has_json = any(f.endswith('.json') for f in files)
    has_md = any(f.endswith('.md') for f in files)
    if do_api and not has_json:
        return 'apiConversation JSON fetch failed — the FAIL: line above carries the remedy', None
    if do_scrape and not has_md:
        why = 'no markdown — see the scrape log under tmp/logs/browser/capture/<provider>/scrape/'
        if had_md:
            why += ' (previous .md retained, now STALE)'
        return (None, why) if do_api else (why, None)
    return None, None


def discover_js(cfg):
    """Build the conversation-id discovery snippet for this provider's link selector / id filter."""
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
    so slow (citation/LaTeX-heavy) conversations aren't scraped before their DOM exists.

    The caller waits again rather than scraping a page it has just decided is not ready:
    exports that DO succeed here take minutes (276s, 341s, 699s in one 27-conversation gemini
    run), so a 15-second verdict is a guess, and proceeding on it costs a whole walk to
    produce the failure it predicted."""
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
              f'    → run: yoga browser capture --provider claude --id {conv_id}'
              f'  # first front https://claude.ai/chat/{conv_id} in Safari',
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


def ids_from_safari(provider, cfg):
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
    if not ids:
        # Zero is a claim about the account, not a no-op (#411): where the page
        # cannot be positively identified as a real, empty listing, an empty
        # discovery is a failure to SEE — a logged-out listing is a login page
        # with zero conversation anchors, and it once read as 'nothing to do'.
        where = safari_eval_js('String(location.href)') or '(URL unreadable)'
        emit(f'FAIL: found 0 conversations at {where} — cannot positively identify '
             f'an empty {provider} listing; most likely Safari is not logged in to '
             f'{provider}. Log in and re-run: yoga browser capture --provider {provider}')
        raise SystemExit(1)
    return ids


def capture_all(provider, ids, api_root, dom_root, navigate=True, mechanisms=()):
    cfg = PROVIDERS[provider]
    do_api = 'API' in mechanisms
    do_scrape = 'DOM' in mechanisms
    js_script = SCRIPT_DIR / provider / 'browser-chat-capture.js'
    # per-conversation scrape diagnostics go under tmp/logs/ (data/input/ holds captured data only)
    scrape_log_dir = REPO_DIR / 'tmp' / 'logs' / 'browser' / 'capture' / provider / 'scrape'
    # The operation is CAPTURE either way — discovery is ids_from_safari, the
    # listing sweep that found the ids; navigate is a mode, not a name. The old
    # label spelled the whole pass 'discover', so a 52-minute capture log opened
    # '--- discover started ---' and a logged-out no-op read 'discover: nothing
    # to do' — wrong twice in five words.
    label = 'capture'
    methods = '+'.join(m for m, on in (('API', do_api), ('DOM', do_scrape)) if on)
    if not ids:
        emit(f'{label}: nothing to do')
        return []
    RUN['total'] += len(ids)
    print(f'--- {label} started {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    emit(f'capturing {len(ids)} conversations ({methods})')
    safari_focus()
    failed = []
    for i, conv_id in enumerate(ids):
        RUN['at'] = f'[{i+1}/{len(ids)}] {conv_id}'
        print(f'[{i+1}/{len(ids)}] {conv_id}')
        # one dir per mechanism, both named by the conversation id (the join key);
        # created only for the mechanism(s) this run performs — no empty twins
        api_dir = api_root / conv_id if do_api else None
        dom_dir = dom_root / conv_id if do_scrape else None
        for d in (api_dir, dom_dir):
            if d is not None:
                d.mkdir(parents=True, exist_ok=True)
        had_md = any(dom_dir.glob('*.md')) if dom_dir is not None else False
        if navigate:
            safari_navigate(cfg['chat_url'].format(id=conv_id))
        start = time.time()
        files = []
        if do_api:
            if navigate:
                wait_for_url(conv_id)
                time.sleep(SETTLE_PAUSE)
            j = fetch_api(conv_id, api_dir)
            if j:
                files.append(j)
        if do_scrape:
            if navigate:
                wait_for_url(conv_id)   # confirm the NEW conversation loaded, not a stale/transitioning page
                if not wait_for_ready(cfg['ready_sel']):
                    print(f'  not rendered after {READY_TIMEOUT}s — waiting {READY_TIMEOUT * 4}s more')
                    if not wait_for_ready(cfg['ready_sel'], timeout=READY_TIMEOUT * 4):
                        # Name the page it is actually on. The scrape is about to fail and say
                        # "wrong page?" as one of three guesses; the URL settles which it is.
                        where = safari_eval_js('String(location.pathname)') or '(URL unreadable)'
                        print(f'  still no {cfg["ready_sel"]} after {READY_TIMEOUT * 5}s at {where} — scraping anyway')
            safari_eval_js(f'window.__capture_progress = "{i + 1}/{len(ids)}"')  # in-page "conversation i/N"
            files += scrape_one(dom_dir, js_script, scrape_log_dir) or []
        fatal, note = outcome(do_api, do_scrape, files, had_md)
        if note:
            print(f'  note: {note}', file=sys.stderr)
        verdict = f'FAILED — {fatal}' if fatal else f'done in {time.time() - start:.0f}s — {", ".join(files) or "(no files)"}'
        emit(f'[{i+1}/{len(ids)}] {conv_id} — {verdict}')
        if fatal:
            failed.append((conv_id, fatal))
        else:
            RUN['done'] += 1
    print(f'--- {label} finished {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} ---')
    RUN['failed'].extend(failed)
    if failed and len(ids) > 1:
        # the sweep's bulk remedy, beside the footer's per-item lines: fix the cause
        # the FAIL lines name, then re-sweep — named as the command a reader types
        print('    → run: yoga browser capture'
              '  # re-sweep after fixing the cause(s) the FAIL lines above name',
              file=sys.stderr)
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--provider', choices=sorted(PROVIDERS),
                    help='restrict to one provider (default: every provider)')
    ap.add_argument('--scope', action='store_true',
                    help='print the providers and mechanisms the restrictions select, then stop — '
                         'so a caller reads the scope off the declaration instead of restating it')
    ap.add_argument('--browser-api', default=None,
                    help='browser-API root (default: data/input/<provider>/chat/browser-API)')
    ap.add_argument('--browser-dom', default=None,
                    help='browser-DOM root (default: data/input/<provider>/chat/browser-DOM)')
    ap.add_argument('--id', metavar='ID',
                    help='Capture ONE conversation — in place if the front tab shows it, '
                         'else navigated to in a work tab; default is to discover and capture all')
    ap.add_argument('--mechanism', choices=['API', 'DOM'], default=None,
                    help='restrict to one mechanism (default: every mechanism this provider has)')
    ap.add_argument('--run-log', default=None,
                    help='the run log safari_capture.sh names: stdout becomes this file '
                         '(line-buffered), the terminal keeps the anchor, one line per '
                         'conversation, and the verdict (#413)')
    args = ap.parse_args()

    # The channel split (#413), before any work: the log is opened and anchored
    # first (#412 — a wordless log is impossible), the terminal kept for the
    # human-altitude lines via TERM/emit, stderr on both.
    global TERM
    if args.run_log:
        # append: browser.sh may have opened this log with the audit preamble
        log_fh = open(args.run_log, 'a', buffering=1)
        TERM = sys.stdout
        sys.stdout = log_fh
        sys.stderr = _BothStreams(log_fh, sys.__stderr__)

    # `<provider> <mechanism>+…` per provider the restrictions leave non-empty. The one
    # place the declaration is read by anyone but this file: browser.sh loops over these
    # lines rather than holding a second copy of which provider has what.
    if args.scope:
        for name, cfg in sorted(PROVIDERS.items()):
            if args.provider and name != args.provider:
                continue
            selected = [m for m in cfg['mechanisms']
                        if args.mechanism is None or m == args.mechanism]
            if selected:
                print(f'{name} {"+".join(selected)}')
        return
    if not args.provider:
        ap.error('--provider is required to capture (--scope reports without capturing)')

    cfg = PROVIDERS[args.provider]
    # Two independent restrictions, intersected. Neither one adds: a mechanism the
    # provider does not have cannot be requested into existence, and an unrestricted
    # run is every mechanism it has. Empty is a real answer, and is said, not guessed.
    mechanisms = tuple(m for m in cfg['mechanisms']
                       if args.mechanism is None or m == args.mechanism)
    if not mechanisms:
        print(f'{args.provider} has no {args.mechanism} mechanism — it has '
              f'{", ".join(cfg["mechanisms"])}; nothing to capture', file=sys.stderr)
        raise SystemExit(1)
    RUN['t0'] = time.time()
    anchor(args.provider, mechanisms, args.id)
    if 'DOM' in mechanisms:
        js_script = SCRIPT_DIR / args.provider / 'browser-chat-capture.js'
        if not js_script.exists():
            print(f'Error: {js_script} not found', file=sys.stderr)
            raise SystemExit(1)

    # one root per mechanism in scope; dirs appear only when captured into
    api_root = Path(args.browser_api or REPO_DIR / 'data' / 'input' / args.provider / 'chat' / 'browser-API').resolve()
    dom_root = Path(args.browser_dom or REPO_DIR / 'data' / 'input' / args.provider / 'chat' / 'browser-DOM').resolve()
    if 'API' in mechanisms:
        api_root.mkdir(parents=True, exist_ok=True)
    if 'DOM' in mechanisms:
        dom_root.mkdir(parents=True, exist_ok=True)

    if args.id:
        # Single capture. If the front tab already shows the conversation, capture it in
        # place (the capture-what-you're-reading workflow: no navigation, browser untouched);
        # otherwise do exactly what discovery mode does for one id — navigate in a dedicated
        # work tab and restore the front tab — so the audit's remedy runs as printed. Either
        # way the id is verified against the page before filing (wait_for_url on the
        # navigating path), never trusted.
        front_url = osascript('tell application "Safari" to get URL of front document')
        if args.id in front_url:
            failed = capture_all(args.provider, [args.id], api_root, dom_root,
                                 navigate=False, mechanisms=mechanisms)
        else:
            prev_tab = safari_open_work_tab()
            try:
                failed = capture_all(args.provider, [args.id], api_root, dom_root,
                                     navigate=True, mechanisms=mechanisms)
            finally:
                safari_close_work_tab(prev_tab)
    else:
        # Discovery mode navigates through every conversation — do that in a dedicated
        # work tab so the user's front tab survives, and restore it afterwards.
        prev_tab = safari_open_work_tab()
        try:
            ids = ids_from_safari(args.provider, cfg)
            write_ordering(cfg, ids, dom_root)
            failed = capture_all(args.provider, ids, api_root, dom_root,
                                 navigate=True, mechanisms=mechanisms)
        finally:
            safari_close_work_tab(prev_tab)
    footer()
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except SendRefused as e:
        # Exit 3, distinct from 1 (captures failed): nothing was attempted, so the run has
        # no result to report -- it was refused before reaching the account.
        print(e, file=sys.stderr)
        raise SystemExit(3)
    except KeyboardInterrupt:
        # A ctrl-C is a verdict the log records, never an eraser (#415): the
        # anchor is already down, everything shown is already flushed
        # (line-buffered), and the footer says how far the run got.
        footer(interrupted=True)
        raise SystemExit(130)
