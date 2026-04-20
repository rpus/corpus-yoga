#!/usr/bin/env python
"""
extract_files.py

Walks conversations.json and extracts file contents from create_file
tool calls, grouped by conversation. Writes files under:

    <output_dir>/<chat_index>_<conversation_name>/<path_from_tool>

Usage:
    python extract_files.py [--conversations PATH] [--out-dir PATH] [--settings PATH]

Defaults:
    --conversations  conversations.json
    --out-dir        extracted_files/
    --settings       settings.json        (optional; overrides defaults)
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Optional


# ── settings ─────────────────────────────────────────────────────────────────

def load_settings(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


# ── extraction ────────────────────────────────────────────────────────────────

def slug(name: str) -> str:
    """Convert conversation name to a safe directory component."""
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '_', s)
    s = s[:60].strip('_')
    return s or 'untitled'


def extract_create_file_calls(message: dict) -> list[dict]:
    """
    Return list of {path, file_text} from create_file tool_use blocks
    in a single chat message.
    """
    results = []
    for block in message.get('content', []):
        if block.get('type') != 'tool_use':
            continue
        if block.get('name') != 'create_file':
            continue
        inp = block.get('input', {})
        path      = inp.get('path', '').strip()
        file_text = inp.get('file_text', '')
        if path:
            results.append({'path': path, 'file_text': file_text})
    return results


def sanitise_path(raw: str) -> Optional[Path]:
    """
    Strip common container prefixes (/home/claude/, /mnt/user-data/outputs/)
    and return a relative Path. Returns None if result looks unsafe.
    """
    p = raw
    for prefix in ('/home/claude/', '/mnt/user-data/outputs/', '/mnt/user-data/'):
        if p.startswith(prefix):
            p = p[len(prefix):]
            break
    # Safety: reject absolute paths and path traversal after stripping
    rel = Path(p)
    if rel.is_absolute():
        return None
    parts = rel.parts
    if '..' in parts:
        return None
    return rel


def process(conversations_path: Path, out_dir: Path) -> None:
    convos = json.loads(conversations_path.read_text())
    convos_sorted = sorted(convos, key=lambda c: c.get('created_at', ''))

    log_path    = out_dir / 'extract_files.log'
    total_files = 0
    with log_path.open('w') as log:
        for idx, convo in enumerate(convos_sorted):
            name     = convo.get('name', 'untitled')
            messages = convo.get('chat_messages', [])

            calls = []
            for msg in messages:
                calls.extend(extract_create_file_calls(msg))

            if not calls:
                continue

            convo_dir = out_dir / f'{idx:03d}_{slug(name)}'
            written = copied = 0
            for call in calls:
                rel = sanitise_path(call['path'])
                if rel is None:
                    log.write(f'  SKIP (unsafe path): {call["path"]}\n')
                    continue
                dest = convo_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(call['file_text'])
                written += 1
                dl_dir = DOWNLOADED_DIR / convo_dir.name
                if not (dl_dir.exists() and list(dl_dir.rglob(rel.name))):
                    rsc_dest = RSC_DIR / convo_dir.name / rel
                    rsc_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, rsc_dest)
                    copied += 1

            if written:
                log.write(f'[{idx:03d}] {name[:60]}  →  {written} file(s), {copied} copied to rsc  ({convo_dir.name})\n')
                total_files += written

        log.write(f'\nDone. {total_files} file(s) extracted.\n')



# ── main ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR     = Path(__file__).parent
OUTPUT_DIR     = SCRIPT_DIR.parent.parent / 'gen'
DOWNLOADED_DIR = SCRIPT_DIR.parent.parent / 'rsc' / 'artifacts' / 'downloaded'
RSC_DIR        = SCRIPT_DIR.parent.parent / 'rsc' / 'artifacts' / 'extracted_files'


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--conversations', default=None)
    parser.add_argument('--data-dir',      default=None)
    parser.add_argument('--out-dir',       default=None)
    parser.add_argument('--settings',      default='settings.json')
    args = parser.parse_args()

    if args.data_dir:
        data_dir           = Path(args.data_dir).resolve()
        conversations_path = data_dir / 'conversations.json'
        out_dir            = Path(args.out_dir) if args.out_dir else OUTPUT_DIR / data_dir.name / 'extracted_files'
    else:
        settings           = load_settings(Path(args.settings))
        conversations_path = Path(args.conversations or settings.get('conversations', 'conversations.json'))
        out_dir            = Path(args.out_dir or settings.get('extracted_files_dir', 'extracted_files'))

    if not conversations_path.exists():
        sys.exit(f'conversations.json not found: {conversations_path}')

    out_dir.mkdir(parents=True, exist_ok=True)
    process(conversations_path, out_dir)


if __name__ == '__main__':
    main()
