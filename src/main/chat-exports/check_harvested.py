#!/usr/bin/env python
"""
check_harvested.py

Cross-references data-files.json against extracted_files/ and
extracted_heredocs/ to report files not yet harvested.

Usage:
    python check_harvested.py <chat-export-name>

Example:
    python check_harvested.py data-2026-04-07-07-52-05-batch-0000
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent.parent.parent / 'gen' / 'chat-exports'

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
    return mime_type is not None and any(mime_type.startswith(p) for p in BINARY_MIME_PREFIXES)


def parse_file_path(file_path_str: str) -> tuple:
    """Return (rel_path, bucket) from a container-absolute file path.

    rel_path: path relative to the container prefix — matches extracted_files and downloaded layout.
    bucket:   'outputs' or 'working' for the extracted_heredocs sub-directory, or None if unknown.

    The caller does not use bucket to filter harvesting checks — in_ef and in_eh search all
    extraction locations exhaustively, so bucket=None does not cause misclassification.
    """
    if file_path_str.startswith('/mnt/user-data/outputs/'):
        return Path(file_path_str[len('/mnt/user-data/outputs/'):]), 'outputs'
    if file_path_str.startswith('/home/claude/'):
        return Path(file_path_str[len('/home/claude/'):]), 'working'
    if file_path_str.startswith('/mnt/user-data/'):
        return Path(file_path_str[len('/mnt/user-data/'):]), None
    return Path(file_path_str.lstrip('/')), None


def main():
    if len(sys.argv) != 2:
        sys.exit(f'Usage: {sys.argv[0]} <chat-export-name>')

    name        = sys.argv[1]
    export_dir  = OUTPUT_DIR / name
    present_dir = export_dir / 'presentation'

    data_files = json.loads((present_dir / 'data-local-resources.json').read_text())
    data_chats = json.loads((present_dir / 'data-chats.json').read_text())

    # Build chat_idx → slug from data-chats
    ci = {c: i for i, c in enumerate(data_chats['columns'])}
    chat_slugs = {
        row[ci['chat']]: f'{row[ci["chat"]]:03d}_{slug(row[ci["name"]])}'
        for row in data_chats['rows']
    }

    extracted_files_dir    = export_dir / 'extracted_files'
    extracted_heredocs_dir = export_dir / 'extracted_heredocs'
    downloaded_dir         = SCRIPT_DIR.parent.parent.parent / 'rsc' / 'artifacts' / 'downloaded'

    cols = {c: i for i, c in enumerate(data_files['columns'])}
    heredocs_ran = extracted_heredocs_dir.exists()
    BUCKETS = ('outputs', 'working')

    unharvested_binary        = []
    unharvested_unrecoverable = []
    unharvested_heredoc       = []
    downloaded_only           = []

    for row in data_files['rows']:
        chat_idx  = row[cols['chat']]
        filename  = row[cols['file']]
        mime_type = row[cols['mime_type']] if 'mime_type' in cols else ''
        chat_slug = chat_slugs.get(chat_idx, f'{chat_idx:03d}_unknown')

        rel_path, bucket = parse_file_path(filename)
        in_ef = (extracted_files_dir / chat_slug / rel_path).exists()
        in_eh = any((extracted_heredocs_dir / chat_slug / b / rel_path).exists() for b in BUCKETS)
        in_gen = in_ef or in_eh
        in_downloaded = (downloaded_dir / chat_slug / rel_path).exists()

        display = str(rel_path)
        if in_gen:
            pass
        elif in_downloaded:
            downloaded_only.append((chat_idx, display))
        else:
            entry = (chat_idx, display)
            if is_binary(mime_type):
                unharvested_binary.append(entry)
            elif heredocs_ran:
                unharvested_unrecoverable.append(entry)
            else:
                unharvested_heredoc.append(entry)

    # Overlaps: same subpath in both extracted_files and extracted_heredocs
    # (bucket prefix stripped from heredocs paths for canonical comparison)
    overlaps = []
    for chat_idx, chat_slug in sorted(chat_slugs.items()):
        ef_dir = extracted_files_dir / chat_slug
        eh_dir = extracted_heredocs_dir / chat_slug
        if not (ef_dir.exists() and eh_dir.exists()):
            continue
        ef_paths = {f.relative_to(ef_dir) for f in ef_dir.rglob('*') if f.is_file()}
        eh_paths = set()
        for f in eh_dir.rglob('*'):
            if f.is_file():
                parts = f.relative_to(eh_dir).parts
                canon = Path(*parts[1:]) if parts[0] in BUCKETS else Path(*parts)
                eh_paths.add(canon)
        for path in sorted(ef_paths & eh_paths):
            overlaps.append((chat_idx, str(path)))

    if overlaps:
        print(f'  ↔ in both extracted_files and extracted_heredocs ({len(overlaps)} file(s)):')
        for chat_idx, f in overlaps:
            print(f'      [{chat_idx:03d}] {f}')

    if downloaded_only:
        print(f'  ↓ in rsc/downloaded only ({len(downloaded_only)} file(s), manually downloaded, not in gen):')
        for chat_idx, f in downloaded_only:
            print(f'      [{chat_idx:03d}] {f}')

    if unharvested_binary:
        print(f'  ⚠ not harvested — binary, download from app ({len(unharvested_binary)} file(s)):')
        for chat_idx, f in unharvested_binary:
            print(f'      [{chat_idx:03d}] {f}')

    if unharvested_unrecoverable:
        print(f'  ⚠ not recoverable from export ({len(unharvested_unrecoverable)} file(s), produced at runtime, not in gen):')
        for chat_idx, f in unharvested_unrecoverable:
            print(f'      [{chat_idx:03d}] {f}')

    if unharvested_heredoc:
        print(f'  ⚠ not harvested — run extract_heredocs.sh ({len(unharvested_heredoc)} file(s)):')
        for chat_idx, f in unharvested_heredoc:
            print(f'      [{chat_idx:03d}] {f}')

    if not any([overlaps, downloaded_only, unharvested_binary, unharvested_unrecoverable, unharvested_heredoc]):
        print('  ✓ data-files: all harvested')


if __name__ == '__main__':
    main()
