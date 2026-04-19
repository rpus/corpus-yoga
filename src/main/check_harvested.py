#!/usr/bin/env python
"""
check_harvested.py

Cross-references data-files.json against extracted_files/ and
extracted_heredocs/ to report files not yet harvested.

Usage:
    python check_harvested.py <data-files.json> <conversations.json> <gen-export-dir>
"""

import json
import re
import sys
from pathlib import Path

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
    data_files_path = Path(sys.argv[1])
    conv_path       = Path(sys.argv[2])
    gen_dir         = Path(sys.argv[3])

    data_files = json.loads(data_files_path.read_text())
    convos     = sorted(json.loads(conv_path.read_text()), key=lambda c: c.get('created_at', ''))
    chat_slugs = {i: f'{i:03d}_{slug(c["name"])}' for i, c in enumerate(convos)}

    extracted_files_dir    = gen_dir / 'extracted_files'
    extracted_heredocs_dir = gen_dir / 'extracted_heredocs'

    cols = {c: i for i, c in enumerate(data_files['columns'])}
    unharvested_binary, unharvested_text = [], []

    for row in data_files['rows']:
        chat_idx  = row[cols['chat']]
        filename  = row[cols['file']]
        mime_type = row[cols.get('mime_type', -1)] if 'mime_type' in cols else ''
        chat_slug = chat_slugs.get(chat_idx, f'{chat_idx:03d}_unknown')

        found = any(
            (base / chat_slug).exists() and list((base / chat_slug).rglob(filename))
            for base in [extracted_files_dir, extracted_heredocs_dir]
        )

        if not found:
            entry = (chat_idx, filename)
            if is_binary(mime_type):
                unharvested_binary.append(entry)
            else:
                unharvested_text.append(entry)

    if unharvested_binary:
        print('  ⚠ not harvested — binary, download from app:')
        for chat_idx, f in unharvested_binary:
            print(f'      [{chat_idx:03d}] {f}')

    if unharvested_text:
        print('  ⚠ not harvested — run extract_heredocs.py:')
        for chat_idx, f in unharvested_text:
            print(f'      [{chat_idx:03d}] {f}')

    if not unharvested_binary and not unharvested_text:
        print('  ✓ data-files: all harvested')


if __name__ == '__main__':
    main()
