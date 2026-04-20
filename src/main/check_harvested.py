#!/usr/bin/env python
"""
check_harvested.py

Cross-references data-files.json against extracted_files/ and
extracted_heredocs/ to report files not yet harvested.

Usage:
    python check_harvested.py <data-export-name>

Example:
    python check_harvested.py data-2026-04-07-07-52-05-batch-0000
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent.parent / 'gen'

BINARY_MIME_PREFIXES = (
    'application/vnd.',
    'application/pdf',
    'application/msword',
    'image/',
    'audio/',
    'video/',
)


def slug(name):
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '_', s)
    return s[:60].strip('_') or 'untitled'


def is_binary(mime_type):
    return any(mime_type.startswith(p) for p in BINARY_MIME_PREFIXES)


def main():
    if len(sys.argv) != 2:
        sys.exit(f'Usage: {sys.argv[0]} <data-export-name>')

    name        = sys.argv[1]
    export_dir  = OUTPUT_DIR / name
    present_dir = export_dir / 'presentation'

    data_files = json.loads((present_dir / 'data-files.json').read_text())
    data_chats = json.loads((present_dir / 'data-chats.json').read_text())

    # Build chat_idx → slug from data-chats
    ci = {c: i for i, c in enumerate(data_chats['columns'])}
    chat_slugs = {
        row[ci['chat']]: f'{row[ci["chat"]]:03d}_{slug(row[ci["name"]])}'
        for row in data_chats['rows']
    }

    extracted_files_dir    = export_dir / 'extracted_files'
    extracted_heredocs_dir = export_dir / 'extracted_heredocs'
    downloaded_dir         = SCRIPT_DIR.parent.parent / 'rsc' / 'artifacts' / 'downloaded'

    cols = {c: i for i, c in enumerate(data_files['columns'])}
    heredocs_ran = extracted_heredocs_dir.exists()

    unharvested_binary       = []
    unharvested_unrecoverable = []
    unharvested_heredoc      = []

    for row in data_files['rows']:
        chat_idx  = row[cols['chat']]
        filename  = row[cols['file']]
        mime_type = row[cols['mime_type']] if 'mime_type' in cols else ''
        chat_slug = chat_slugs.get(chat_idx, f'{chat_idx:03d}_unknown')

        found = any(
            (base / chat_slug).exists() and list((base / chat_slug).rglob(filename))
            for base in [extracted_files_dir, extracted_heredocs_dir, downloaded_dir]
        )

        if not found:
            entry = (chat_idx, filename)
            if is_binary(mime_type):
                unharvested_binary.append(entry)
            elif heredocs_ran:
                unharvested_unrecoverable.append(entry)
            else:
                unharvested_heredoc.append(entry)

    if unharvested_binary:
        print('  ⚠ not harvested — binary, download from app:')
        for chat_idx, f in unharvested_binary:
            print(f'      [{chat_idx:03d}] {f}')

    if unharvested_unrecoverable:
        print('  ⚠ not recoverable from export — produced at runtime:')
        for chat_idx, f in unharvested_unrecoverable:
            print(f'      [{chat_idx:03d}] {f}')

    if unharvested_heredoc:
        print('  ⚠ not harvested — run extract_heredocs.sh:')
        for chat_idx, f in unharvested_heredoc:
            print(f'      [{chat_idx:03d}] {f}')

    if not any([unharvested_binary, unharvested_unrecoverable, unharvested_heredoc]):
        print('  ✓ data-files: all harvested')


if __name__ == '__main__':
    main()
