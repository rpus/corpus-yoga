"""
Shared Safari automation utilities for browser-captures scripts.
Called by safari_capture.py and safari_fetch_api_json.py — do not invoke directly.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

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


def osascript(code):
    r = subprocess.run(['osascript', '-e', code], capture_output=True, text=True)
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
    code = (
        f'set jsCode to read POSIX file "{js_path}" as «class utf8»\n'
        'tell application "Safari" to do JavaScript jsCode in front document'
    )
    subprocess.run(['osascript', '-e', code], capture_output=True)


def safari_eval_js(js_code):
    """Evaluate a JS string in Safari's front document and return the result."""
    escaped = js_code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    r = subprocess.run(
        ['osascript', '-e', f'tell application "Safari" to do JavaScript "{escaped}" in front document'],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f'osascript error: {r.stderr.strip()}', file=sys.stderr)
    return r.stdout.strip()


def safari_fetch_api_json(uuid, timeout=DOWNLOAD_TIMEOUT):
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
    input/) and the .log into log_dir (under logs/ -- input/ holds data only). The .log holds
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
        # claude path's curated FAIL), never a bare traceback: the 2026-07-11
        # shortcut run died raw here while claude's error explained itself.
        print(f'FAIL: macOS denied reading {DOWNLOADS} from this process chain:\n'
              f'    {process_chain()}\n'
              '    grant the outermost app Downloads access (System Settings → Privacy & '
              'Security; Full Disk Access takes manual additions where Files and Folders '
              f'shows nothing). The scraped files are stranded in ~/Downloads — move the '
              f'.md into {dest_dir} and the .log into {log_dir} by hand, or recapture '
              'from an already-granted Terminal:\n'
              f'    → run: src/main/browser-captures/safari_capture.sh '
              f'--agent {dest_dir.parent.name} --id {dest_dir.name}'
              '  # first front the conversation in Safari',
              file=sys.stderr)
        return moved
    for f in downloads:
        if f.stat().st_mtime <= after_time:
            continue
        if f.suffix == '.log':
            print(_colour_log_levels(f.read_text()), end='')
            # name the diagnostic log by the conversation id (the dir), not the page title: on a
            # failed scrape the title is junk, and a stable name overwrites rather than accumulates
            shutil.move(str(f), log_dir / f'{dest_dir.name}.log')
        elif f.suffix == '.md':
            shutil.move(str(f), dest_dir / f.name)
            moved.append(f.name)
    if moved:
        # a successful scrape supersedes any previous .md whose title slug has since
        # changed — remove it, or downstream globs would see two markdowns per datum.
        # (On a FAILED scrape nothing is touched: the old .md is retained, as STALE.)
        for old in dest_dir.glob('*.md'):
            if old.name not in moved:
                old.unlink()
                print(f'  removed superseded {old.name}')
    return moved
