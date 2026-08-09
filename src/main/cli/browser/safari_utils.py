"""
Shared Safari automation utilities for browser-captures scripts.
Called by safari_capture.py and audit_captures.py — do not invoke directly.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SELF = 'src/main/cli/browser/safari_utils.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))  # src/main/ on the path
from markdown_projection import turn_extent  # noqa: E402 — the format authority owns the parsers
from send import SendRefused, assert_may_send  # noqa: E402,F401 — every outward call below passes through it


DOWNLOADS        = Path.home() / 'Downloads'
PAGE_LOAD_WAIT   = 3
DOWNLOAD_TIMEOUT = 30

FETCH_API_JSON_JS = """
(async function() {
  const orgId = document.cookie.match(/lastActiveOrg=([^;]+)/)?.[1];
  const uuid  = window.location.pathname.split('/').pop();
  if (!orgId || !uuid) return;
  const r = await fetch('/api/organizations/' + orgId + '/chat_conversations/' + uuid
    + '?tree=true&rendering_mode=messages&render_all_tools=true', {credentials: 'include'});
  if (!r.ok) return;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(await r.json(), null, 2)],
    {type: 'application/json'}));
  a.download = uuid + '.json';
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(a.href);
})();
"""


# Every Apple Event is bounded (#414): osascript against a wedged, beach-balling
# page blocks INDEFINITELY otherwise — below every python-level watchdog, which
# is how one tiny hung conversation held a whole sweep hostage. Generous, because
# a legitimate 'do JavaScript' on a heavy DOM can be slow; on expiry the call
# fails loudly naming itself, and the sweep records that conversation and moves on.
OSASCRIPT_TIMEOUT = 60


def osascript(code, timeout=OSASCRIPT_TIMEOUT):
    assert_may_send(f'osascript: {code[:60]}')
    try:
        r = subprocess.run(['osascript', '-e', code], capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f'FAIL: osascript did not answer within {timeout}s (Safari wedged?): '
              f'{code[:80]}', file=sys.stderr)
        return ''
    return r.stdout.strip()


def safari_focus():
    osascript('tell application "Safari" to activate')
    time.sleep(1)
    if osascript('tell application "Safari" to count windows') == '0':
        osascript('tell application "Safari" to make new document')
        time.sleep(1)
    safari_assert_js_allowed()


def safari_assert_js_allowed():
    """Fail fast if Safari rejects 'do JavaScript' via Apple Events. Without this,
    every injection silently evaluates to '' and discovery 'finds' 0 conversations —
    a hard setup failure disguised as an empty result."""
    # A preflight is still a SEND — an Apple Event driving the browser — and this was
    # the one direct osascript call in the module without the assert its siblings
    # carry (the 2026-07-28 python census, PR #114).
    assert_may_send('Safari do-JavaScript preflight')
    r = subprocess.run(
        ['osascript', '-e', 'tell application "Safari" to do JavaScript "1+1" in front document'],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.exit(
            f'error: Safari blocked JavaScript from Apple Events: {r.stderr.strip()}\n'
            'Enable it via Safari → Settings → Advanced → "Show features for web developers",\n'
            'then Settings → Developer → "Allow JavaScript from Apple Events" — and re-run.'
        )


def safari_navigate(url):
    osascript(f'tell application "Safari" to set URL of front document to "{url}"')


def safari_open_work_tab():
    """Open a dedicated work tab (and select it) so multi-conversation captures don't
    hijack whatever page the user had in their front tab. Returns the index of the
    previously-selected tab, for safari_close_work_tab to restore. The work tab must
    stay the CURRENT tab: Safari throttles timers and rendering in background tabs,
    which would starve the scraper's scroll/settle loops."""
    safari_focus()
    prev = osascript('tell application "Safari" to get index of current tab of front window')
    osascript('tell application "Safari" to tell front window to set current tab to (make new tab at end of tabs)')
    time.sleep(1)
    return prev


def safari_close_work_tab(prev_index):
    """Close the work tab and restore the user's previously-selected tab."""
    osascript('tell application "Safari" to tell front window to close current tab')
    if prev_index:
        osascript(f'tell application "Safari" to tell front window to set current tab to tab {prev_index}')




def safari_run_js_file(js_path):
    assert_may_send(f'inject {js_path}')
    code = (
        f'set jsCode to read POSIX file "{js_path}" as «class utf8»\n'
        'tell application "Safari" to do JavaScript jsCode in front document'
    )
    try:
        subprocess.run(['osascript', '-e', code], capture_output=True,
                       timeout=OSASCRIPT_TIMEOUT)
    except subprocess.TimeoutExpired:
        print(f'FAIL: scrape injection did not answer within {OSASCRIPT_TIMEOUT}s '
              f'(Safari wedged?): {js_path}', file=sys.stderr)


def safari_eval_js(js_code):
    """Evaluate a JS string in Safari's front document and return the result."""
    assert_may_send(f'evaluate JS: {js_code[:60]}')
    escaped = js_code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    try:
        r = subprocess.run(
            ['osascript', '-e', f'tell application "Safari" to do JavaScript "{escaped}" in front document'],
            capture_output=True, text=True, timeout=OSASCRIPT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        print(f'FAIL: Safari did not answer within {OSASCRIPT_TIMEOUT}s (wedged page?): '
              f'{js_code[:60]}', file=sys.stderr)
        return ''
    if r.returncode != 0:
        print(f'osascript error: {r.stderr.strip()}', file=sys.stderr)
    return r.stdout.strip()


def safari_fetch_api_json(uuid, timeout=DOWNLOAD_TIMEOUT):
    assert_may_send(f'fetch the API JSON of conversation {uuid}')
    escaped = FETCH_API_JSON_JS.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    start = time.time()
    osascript(f'tell application "Safari" to do JavaScript "{escaped}" in front document')
    deadline = start + timeout
    while time.time() < deadline:
        for f in DOWNLOADS.glob(f'{uuid}.json'):
            if f.stat().st_mtime > start:
                return f
        time.sleep(0.5)
    return None


def safari_fetch_asset(url_path, filename, timeout=DOWNLOAD_TIMEOUT):
    """Fetch a session-authenticated asset URL (#422 — the file handles the API
    capture names, e.g. /api/<org>/files/<uuid>/document_pdf) in the front
    claude.ai page and download it as `filename`; returns the Downloads path,
    or None when the fetch produced nothing within the timeout."""
    assert_may_send(f'fetch asset {url_path}')
    js = (
        "(async function() {"
        f"  const r = await fetch({json.dumps(url_path)}, {{credentials: 'include'}});"
        "  if (!r.ok) return;"
        "  const a = document.createElement('a');"
        "  a.href = URL.createObjectURL(await r.blob());"
        f"  a.download = {json.dumps(filename)};"
        "  document.body.appendChild(a); a.click();"
        "  document.body.removeChild(a); URL.revokeObjectURL(a.href);"
        "})();"
    )
    start = time.time()
    safari_eval_js(js)
    deadline = start + timeout
    while time.time() < deadline:
        for f in DOWNLOADS.glob('*'):
            # Safari may dedupe a colliding name to 'name (1).ext' — accept any
            # fresh arrival whose stem starts with the asked-for stem.
            if f.stat().st_mtime > start and f.name.startswith(Path(filename).stem):
                return f
        time.sleep(0.5)
    return None


def wait_for_log(after_time, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for f in DOWNLOADS.glob('*.log'):
            if f.stat().st_mtime > after_time:
                return f
        time.sleep(1)
    return None


_LEVEL_COLOUR = {'ERROR': '\033[31m', 'WARN': '\033[33m'}  # red, yellow (mirrors the in-page status box)
_RESET = '\033[0m'


def _colour_log_levels(text):
    """Colour each capture-log line by its [LEVEL] tag (ERROR red, WARN yellow), for TTY output
    only -- so a tee'd logfile or piped output stays plain. The [LEVEL] label is present either way."""
    if not sys.stdout.isatty():
        return text
    out = []
    for line in text.split('\n'):
        colour = next((c for lvl, c in _LEVEL_COLOUR.items() if f'[{lvl}]' in line), '')
        out.append(f'{colour}{line}{_RESET}' if colour else line)
    return '\n'.join(out)


def process_chain() -> str:
    """This process's ancestry (comm names, child ← parent), for TCC forensics:
    macOS attributes a file-access denial to some app up this chain, and which
    one is not knowable from here — so name them all and let the reader grant
    the outermost real app."""
    import os
    chain, pid = [], os.getpid()
    for _ in range(12):
        out = subprocess.run(['ps', '-o', 'ppid=,comm=', '-p', str(pid)],
                             capture_output=True, text=True).stdout.split(None, 1)
        if len(out) < 2:
            break
        chain.append(out[1].strip().rsplit('/', 1)[-1])
        pid = int(out[0])
        if pid <= 1:
            break
    return ' ← '.join(chain)


def collect_md_and_log(after_time, dest_dir, log_dir):
    """Move freshly-downloaded .md files into dest_dir (the capture's data directory under
    data/input/) and the .log into log_dir (under tmp/logs/ -- data/input/ holds data only). The .log holds
    the in-browser capture log -- including errors like 'No copy buttons found!' -- so it
    is PERSISTED (and printed), not discarded: a failed scrape must leave its error in the
    filesystem, not merely scroll past the terminal. An empty return means the scrape
    produced no markdown (a failure -- read the log)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    moved = []
    try:
        downloads = sorted(DOWNLOADS.iterdir())
    except PermissionError:
        # macOS TCC: the same wall fetch_api hits — word it identically (the
        # claude path's curated FAIL), never a bare traceback: an uncaught failure
        # here dies raw while the claude path's error explains itself.
        print(f'FAIL: macOS denied reading {DOWNLOADS} from this process chain:\n'
              f'    {process_chain()}\n'
              '    grant the outermost app Downloads access (System Settings → Privacy & '
              'Security; Full Disk Access takes manual additions where Files and Folders '
              f'shows nothing). The scraped files are stranded in ~/Downloads — move the '
              f'.md into {dest_dir} and the .log into {log_dir} by hand, or recapture '
              'from an already-granted Terminal:\n'
              f'    → run: yoga browser capture '
              f'--provider {dest_dir.parent.name} --id {dest_dir.name}'
              '  # first front the conversation in Safari',
              file=sys.stderr)
        return moved
    fresh_md = []
    for f in downloads:
        if f.stat().st_mtime <= after_time:
            continue
        if f.suffix == '.log':
            print(_colour_log_levels(f.read_text()), end='')
            # name the diagnostic log by the conversation id (the dir), not the page title: on a
            # failed scrape the title is junk, and a stable name overwrites rather than accumulates
            shutil.move(str(f), log_dir / f'{dest_dir.name}.log')
        elif f.suffix == '.md':
            fresh_md.append(f)

    # L4 at the one point a capture BECOMES the record. These conversations are
    # append-only, so a walk that ends up shorter than what is already here did not
    # shrink the conversation -- it failed partway (the page renders only its last few
    # human turns until the walk reaches the top). Both writes below destroy turns: the
    # move overwrites a same-named .md, and the supersession unlink removes the previous
    # one outright when the title slug has changed. So the comparison happens before
    # either, over the whole directory, and a short capture is treated as the failed
    # scrape it is -- which already has correct behaviour here: nothing is touched, and
    # the existing .md is retained as STALE.
    if fresh_md:
        before = max((turn_extent(m.read_text()) for m in dest_dir.glob('*.md')), default=(0, 0))
        after = max((turn_extent(m.read_text()) for m in fresh_md), default=(0, 0))
        if before > (0, 0) and (after[0] < before[0] or after[1] < before[1]):
            # kept, not discarded: the short capture is the evidence for why this failed
            for m in fresh_md:
                shutil.move(str(m), log_dir / f'{dest_dir.name}.short.md')
            print(f'  REFUSED: this walk captured {after[0]} human turns of {after[1]}, '
                  f'against {before[0]} of {before[1]} already recorded — an append-only '
                  f'conversation cannot shrink, so the walk failed partway. The record is '
                  f'untouched; the short capture is kept at '
                  f'{log_dir / f"{dest_dir.name}.short.md"}')
            print(f'    → run: yoga browser capture --provider {dest_dir.parent.parent.parent.name} '
                  f'--id {dest_dir.name}  # retry the walk')
            return []
        for m in fresh_md:
            shutil.move(str(m), dest_dir / m.name)
            moved.append(m.name)
    if moved:
        # a successful scrape supersedes any previous .md whose title slug has since
        # changed — remove it, or downstream globs would see two markdowns per datum.
        # (On a FAILED scrape nothing is touched: the old .md is retained, as STALE.)
        for old in dest_dir.glob('*.md'):
            if old.name not in moved:
                old.unlink()
                print(f'  removed superseded {old.name}')
    return moved
