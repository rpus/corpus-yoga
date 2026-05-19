#!/usr/bin/env python
"""
Capture markdown and live API JSON for all conversations in ext/browser-captures/.

For each UUID directory, navigates Safari to the conversation, injects
browser-chat-capture.js to export as markdown, and fetches the live API JSON.
Always overwrites previous captures — conversations grow over time.

Requires Safari open, focused, and logged into claude.ai throughout.
Called by safari_capture.sh — do not invoke directly.

Usage:
    python safari_capture.py --browser-captures ext/browser-captures
"""

import argparse, shutil, sys, time
from pathlib import Path

from safari_utils import (
    safari_focus, safari_navigate, safari_run_js_file,
    safari_fetch_api_json, wait_for_log, collect_md_and_log,
    PAGE_LOAD_WAIT,
)

REPO_DIR       = Path(__file__).resolve().parents[3]
JS_SCRIPT      = Path(__file__).parent / 'browser-chat-capture.js'
APPLESCRIPT    = Path('/tmp/claude-safari-capture.applescript')
EXPORT_TIMEOUT = 900
SETTLE_PAUSE   = 2


def capture_one(uuid, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    safari_navigate(f'https://claude.ai/chat/{uuid}')
    time.sleep(PAGE_LOAD_WAIT)

    start = time.time()
    safari_run_js_file(JS_SCRIPT, APPLESCRIPT)
    print(f'  script injected, waiting...')

    log = wait_for_log(start, EXPORT_TIMEOUT)
    if log is None:
        print(f'  TIMEOUT after {EXPORT_TIMEOUT}s — skipping')
        return

    time.sleep(SETTLE_PAUSE)
    files = collect_md_and_log(start, out_dir)

    json_file = safari_fetch_api_json(uuid)
    if json_file:
        md_files = list(out_dir.glob('*.md'))
        stem = md_files[0].stem if md_files else uuid
        shutil.move(str(json_file), out_dir / f'{stem}.json')
        files.append(f'{stem}.json')
    else:
        print(f'  warning: API JSON fetch timed out')

    print(f'  done in {time.time() - start:.0f}s — {", ".join(files)}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', required=True,
                    help='Path to ext/browser-captures/ — re-captures all UUID subdirectories')
    args = ap.parse_args()

    if not JS_SCRIPT.exists():
        print(f'Error: {JS_SCRIPT} not found', file=sys.stderr)
        raise SystemExit(1)

    captures_root = Path(args.browser_captures).resolve()
    uuid_dirs = sorted(d for d in captures_root.iterdir() if d.is_dir())

    log_fh = open(captures_root / 'run.log', 'a', buffering=1)
    sys.stdout = sys.stderr = log_fh

    print(f'--- run started {time.strftime("%Y-%m-%dT%H:%M:%S")} ---')
    print(f'capturing {len(uuid_dirs)} conversations')

    safari_focus()
    for i, uuid_dir in enumerate(uuid_dirs):
        uuid = uuid_dir.name
        print(f'[{i+1}/{len(uuid_dirs)}] {uuid}')
        capture_one(uuid, uuid_dir)

    print(f'--- run finished {time.strftime("%Y-%m-%dT%H:%M:%S")} ---')
    log_fh.close()


if __name__ == '__main__':
    main()
