#!/usr/bin/env python3
"""
Run claude-chat-exporter.js against every conversation in a bulk export,
sequentially, via Safari automation.

Requires:
  - Safari open, focused, and logged into claude.ai throughout
  - src/main/browser-captures/browser-chat-capture.js present (bundled in this repo)

Called by safari_capture.sh — do not invoke directly.
"""

import argparse, json, shutil, subprocess, sys, time
from pathlib import Path

REPO_DIR    = Path(__file__).resolve().parents[3]
JS_SCRIPT   = Path(__file__).parent / 'browser-chat-capture.js'
DOWNLOADS   = Path.home() / 'Downloads'
APPLESCRIPT = Path('/tmp/claude-safari-capture.applescript')

PAGE_LOAD_WAIT    = 4
EXPORT_TIMEOUT    = 900
SETTLE_PAUSE      = 2
JSON_TIMEOUT      = 30

FETCH_JSON_JS = """
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


def safari_run_js():
    APPLESCRIPT.write_text(
        f'set jsCode to read POSIX file "{JS_SCRIPT}" as «class utf8»\n'
        'tell application "Safari" to do JavaScript jsCode in front document\n'
    )
    subprocess.run(['osascript', str(APPLESCRIPT)], capture_output=True)


def safari_fetch_json(uuid):
    escaped = FETCH_JSON_JS.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    start = time.time()
    osascript(f'tell application "Safari" to do JavaScript "{escaped}" in front document')
    deadline = start + JSON_TIMEOUT
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


def collect_outputs(after_time, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    moved = []
    for f in DOWNLOADS.iterdir():
        if f.stat().st_mtime > after_time and f.suffix in ('.md', '.log'):
            shutil.move(str(f), dest_dir / f.name)
            moved.append(f.name)
    return moved


def run_one(export_dir, output=None):
    conversations_json = export_dir / 'conversations.json'
    if not conversations_json.exists():
        print(f"Error: {conversations_json} not found")
        raise SystemExit(1)

    convs = json.load(open(conversations_json))
    out_root = Path(output) if output else \
               REPO_DIR.parent / 'browser-captures' / export_dir.name
    out_root.mkdir(parents=True, exist_ok=True)

    log_fh = open(out_root / 'run.log', 'a', buffering=1)
    sys.stdout = sys.stderr = log_fh

    print(f"--- run started {time.strftime('%Y-%m-%dT%H:%M:%S')} ---")
    print(f"Exporting {len(convs)} conversations from {export_dir.name}")

    for i, conv in enumerate(convs):
        uuid = conv['uuid']
        name = (conv.get('name') or 'untitled')[:60]
        out_dir = out_root / uuid

        print(f"[{i+1}/{len(convs)}] {name}  ({uuid})")

        if out_dir.exists():
            print(f"  Skipped (already exported)")
            continue

        safari_navigate(f'https://claude.ai/chat/{uuid}')
        time.sleep(PAGE_LOAD_WAIT)

        start = time.time()
        safari_run_js()
        print(f"  Script injected, waiting...")

        log = wait_for_log(start, EXPORT_TIMEOUT)
        if log is None:
            print(f"  TIMEOUT after {EXPORT_TIMEOUT}s — skipping")
            continue

        time.sleep(SETTLE_PAUSE)
        files = collect_outputs(start, out_dir)

        # Fetch API JSON while still on the page
        md_files = list(out_dir.glob('*.md'))
        stem = md_files[0].stem if md_files else uuid
        json_download = safari_fetch_json(uuid)
        if json_download:
            shutil.move(str(json_download), out_dir / f'{stem}.json')
            files.append(f'{stem}.json')
        else:
            print(f"  Warning: API JSON fetch timed out")

        print(f"  Done in {time.time() - start:.0f}s — {', '.join(files)}")

    print(f"--- run finished {time.strftime('%Y-%m-%dT%H:%M:%S')} ---")
    log_fh.close()


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--chat-export',
                   help='Path to a single bulk export directory (containing conversations.json)')
    g.add_argument('--chat-exports',
                   help='Path to a directory of bulk export directories (iterates over all data-*/)')
    ap.add_argument('--output', default=None,
                    help='Output root for --chat-export (default: gen/browser-captures/<export-name>/)')
    args = ap.parse_args()

    if not JS_SCRIPT.exists():
        print(f"Error: {JS_SCRIPT} not found", file=sys.stderr)
        raise SystemExit(1)

    safari_focus()

    if args.chat_export:
        run_one(Path(args.chat_export).resolve(), args.output)
    else:
        for d in sorted(Path(args.chat_exports).resolve().glob('data-*/')):
            if d.is_dir():
                run_one(d)


if __name__ == '__main__':
    main()
