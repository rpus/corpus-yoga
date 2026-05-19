"""
Shared Safari automation utilities for browser-captures scripts.
Called by safari_capture.py and safari_fetch_api_json.py — do not invoke directly.
"""
import shutil
import subprocess
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


def safari_navigate(url):
    osascript(f'tell application "Safari" to set URL of front document to "{url}"')


def safari_run_js_file(js_path, applescript_tmp):
    Path(applescript_tmp).write_text(
        f'set jsCode to read POSIX file "{js_path}" as «class utf8»\n'
        'tell application "Safari" to do JavaScript jsCode in front document\n'
    )
    subprocess.run(['osascript', str(applescript_tmp)], capture_output=True)


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


def collect_md_and_log(after_time, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    moved = []
    for f in DOWNLOADS.iterdir():
        if f.stat().st_mtime > after_time and f.suffix in ('.md', '.log'):
            shutil.move(str(f), dest_dir / f.name)
            moved.append(f.name)
    return moved
