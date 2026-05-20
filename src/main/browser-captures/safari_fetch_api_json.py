#!/usr/bin/env python
"""
Backfill live API JSON for browser-captures that have markdown but no JSON.

Used for captures made via shortcut mode (AppleScript), which captures markdown
only. For captures made via safari_capture.py, the JSON is already fetched inline.

Requires Safari open, focused, and logged into claude.ai throughout.
Called by safari_fetch_api_json.sh — do not invoke directly.

Usage:
    python safari_fetch_api_json.py --browser-captures ext/browser-captures
"""

import argparse, shutil, time
from pathlib import Path

from safari_utils import safari_focus, safari_navigate, safari_fetch_api_json

REPO_DIR = Path(__file__).resolve().parents[3]


def fetch_one(uuid_dir):
    uuid     = uuid_dir.name
    md_files = list(uuid_dir.glob('*.md'))
    stem     = md_files[0].stem if md_files else uuid
    dest     = uuid_dir / f'{stem}.json'

    if dest.exists():
        print(f'  skipped (already fetched)')
        return

    safari_navigate(f'https://claude.ai/chat/{uuid}')
    time.sleep(3)

    downloaded = safari_fetch_api_json(uuid)
    if downloaded is None:
        print(f'  TIMEOUT — no download')
        return

    shutil.move(str(downloaded), dest)
    print(f'  saved {dest.name} ({dest.stat().st_size:,} bytes)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', required=True,
                    help='Path to ext/browser-captures/ — backfills JSON for all UUID subdirectories')
    args = ap.parse_args()

    captures_root = Path(args.browser_captures).resolve()
    uuid_dirs = sorted(d for d in captures_root.iterdir() if d.is_dir())

    print(f'--- run started {time.strftime("%Y-%m-%dT%H:%M:%S")} ---')
    print(f'backfilling API JSON for {len(uuid_dirs)} conversations')

    safari_focus()
    for i, uuid_dir in enumerate(uuid_dirs):
        print(f'[{i+1}/{len(uuid_dirs)}] {uuid_dir.name}')
        fetch_one(uuid_dir)

    print(f'--- run finished {time.strftime("%Y-%m-%dT%H:%M:%S")} ---')


if __name__ == '__main__':
    main()
