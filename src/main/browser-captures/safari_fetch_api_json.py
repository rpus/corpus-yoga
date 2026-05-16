#!/usr/bin/env python
"""
Fetch the live API JSON for each conversation and save it alongside the
safari-capture outputs for schema validation.

For each UUID directory under the captures root that lacks a *_data.json file,
navigates Safari to the conversation and injects a small fetch+download snippet.

Called by safari_fetch_api_json.sh — do not invoke directly.
"""

import argparse, shutil, subprocess, time, sys
from pathlib import Path

REPO_DIR    = Path(__file__).resolve().parents[3]
DOWNLOADS   = Path.home() / 'Downloads'
APPLESCRIPT = Path('/tmp/claude-api-fetch.applescript')

PAGE_LOAD_WAIT = 3
DOWNLOAD_TIMEOUT = 30

FETCH_JS = """
(async function() {
  const orgId = document.cookie.match(/lastActiveOrg=([^;]+)/)?.[1];
  const uuid  = window.location.pathname.split('/').pop();
  if (!orgId || !uuid) { console.error('Could not get org/uuid'); return; }
  const url = '/api/organizations/' + orgId + '/chat_conversations/' + uuid
            + '?tree=true&rendering_mode=messages&render_all_tools=true';
  const r = await fetch(url, { credentials: 'include' });
  if (!r.ok) { console.error('API error', r.status); return; }
  const data = await r.json();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
  a.download = uuid + '.json';
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(a.href);
})();
"""


def osascript(code):
    subprocess.run(['osascript', '-e', code], capture_output=True)


def safari_focus():
    osascript('tell application "Safari" to activate')
    time.sleep(1)
    win_count = subprocess.run(
        ['osascript', '-e', 'tell application "Safari" to count windows'],
        capture_output=True, text=True).stdout.strip()
    if win_count == '0':
        osascript('tell application "Safari" to make new document')
        time.sleep(1)


def safari_navigate(url):
    osascript(f'tell application "Safari" to set URL of front document to "{url}"')


def safari_run_js(js):
    APPLESCRIPT.write_text(
        f'tell application "Safari" to do JavaScript "{js.strip()}" in front document\n'
    )
    subprocess.run(['osascript', str(APPLESCRIPT)], capture_output=True)


def wait_for_download(stem, after_time, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for f in DOWNLOADS.glob(f'{stem}.json'):
            if f.stat().st_mtime > after_time:
                return f
        time.sleep(0.5)
    return None


def run_one(captures_root):
    uuid_dirs = sorted(d for d in captures_root.iterdir() if d.is_dir())
    log_fh = open(captures_root / 'fetch_api_json.log', 'a', buffering=1)
    sys.stdout = sys.stderr = log_fh

    print(f"--- run started {time.strftime('%Y-%m-%dT%H:%M:%S')} ---")
    print(f"Fetching API JSON for {len(uuid_dirs)} conversations in {captures_root.name}")

    escaped_js = FETCH_JS.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')

    for i, uuid_dir in enumerate(uuid_dirs):
        uuid = uuid_dir.name
        md_files = list(uuid_dir.glob('*.md'))
        stem = md_files[0].stem if md_files else uuid
        dest = uuid_dir / f'{stem}.json'

        print(f"[{i+1}/{len(uuid_dirs)}] {uuid}")

        if dest.exists():
            print(f"  Skipped (already fetched)")
            continue

        safari_navigate(f'https://claude.ai/chat/{uuid}')
        time.sleep(PAGE_LOAD_WAIT)

        start = time.time()
        safari_run_js(escaped_js)

        downloaded = wait_for_download(uuid, start, DOWNLOAD_TIMEOUT)
        if downloaded is None:
            print(f"  TIMEOUT — no download after {DOWNLOAD_TIMEOUT}s")
            continue

        shutil.move(str(downloaded), dest)
        print(f"  Saved {dest.name} ({dest.stat().st_size:,} bytes)")

    print(f"--- run finished {time.strftime('%Y-%m-%dT%H:%M:%S')} ---")
    log_fh.close()


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--browser-capture',
                   help='Path to a single browser-captures/<batch>/ directory')
    g.add_argument('--browser-captures',
                   help='Path to gen/browser-captures/ — iterates over all batch directories')
    args = ap.parse_args()

    safari_focus()

    if args.browser_capture:
        run_one(Path(args.browser_capture).resolve())
    else:
        for d in sorted(Path(args.browser_captures).resolve().iterdir()):
            if d.is_dir():
                run_one(d)


if __name__ == '__main__':
    main()
