#!/usr/bin/env python
"""
extract_files.py

Walks conversations.json and extracts file contents from create_file
tool calls,.

Group output by conversation under:

    gen/<export-name>/extracted_files/<chat_index>_<conversation_name>/<path_from_tool>

Usage:
    python extract_files.py --data-dir <path-to-export>
    python extract_files.py --data-dir <path> --out-dir <override-output-dir>
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Optional


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

    log_path = out_dir / 'extract_files.log'
    skips: list[str] = []
    rows:  list[tuple] = []   # (idx, name, extracted, downloaded, copied)

    for idx, convo in enumerate(convos_sorted):
        name     = convo.get('name', 'untitled')
        messages = convo.get('chat_messages', [])

        # Collect calls; last write for each path wins (Claude often revises files)
        by_path: dict[str, dict] = {}
        for msg in messages:
            for call in extract_create_file_calls(msg):
                rel = sanitise_path(call['path'])
                if rel is None:
                    skips.append(f'  SKIP (unsafe path): {call["path"]}')
                    continue
                by_path[str(rel)] = {'rel': rel, 'file_text': call['file_text']}

        if not by_path:
            continue

        convo_dir = out_dir / f'{idx:03d}_{slug(name)}'
        extracted = downloaded = copied = 0
        for entry in by_path.values():
            rel = entry['rel']
            dest = convo_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(entry['file_text'])
            extracted += 1
            dl_dir = DOWNLOADED_DIR / convo_dir.name
            if (dl_dir / rel).exists():
                downloaded += 1
            else:
                rsc_dest = RSC_DIR / convo_dir.name / rel
                rsc_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, rsc_dest)
                copied += 1

        rows.append((idx, name[:50], extracted, downloaded, copied))

    with log_path.open('w') as log:
        if skips:
            log.write('\n'.join(skips) + '\n\n')

        if rows:
            nw = max(len(r[1]) for r in rows)
            hdr = f'  {"":3}  {"name":<{nw}}  {"extracted":>9}  {"downloaded":>10}  {"copied":>6}\n'
            sep = f'  {"":3}  {"-"*nw}  {"-"*9}  {"-"*10}  {"-"*6}\n'
            log.write(hdr + sep)
            for idx, name, extracted, downloaded, copied in rows:
                log.write(f'  {idx:03d}  {name:<{nw}}  {extracted:>9}  {downloaded:>10}  {copied:>6}\n')
            t_ext = sum(r[2] for r in rows)
            t_dl  = sum(r[3] for r in rows)
            t_cp  = sum(r[4] for r in rows)
            log.write(sep)
            log.write(f'  {"":3}  {"TOTAL":<{nw}}  {t_ext:>9}  {t_dl:>10}  {t_cp:>6}\n')
        else:
            t_ext = t_dl = t_cp = 0
        log.write(f'\nDone. {t_ext} extracted, {t_dl} already downloaded, {t_cp} copied to rsc.\n')



# ── main ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR     = Path(__file__).parent
OUTPUT_DIR     = SCRIPT_DIR.parent.parent / 'gen' / 'data-exports'
DOWNLOADED_DIR = SCRIPT_DIR.parent.parent / 'rsc' / 'artifacts' / 'downloaded'
RSC_DIR        = SCRIPT_DIR.parent.parent / 'rsc' / 'artifacts' / 'extracted_files'


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--out-dir',  default=None)
    args = parser.parse_args()

    data_dir           = Path(args.data_dir).resolve()
    conversations_path = data_dir / 'conversations.json'
    out_dir            = Path(args.out_dir) if args.out_dir else OUTPUT_DIR / data_dir.name / 'extracted_files'

    if not conversations_path.exists():
        sys.exit(f'conversations.json not found: {conversations_path}')

    out_dir.mkdir(parents=True, exist_ok=True)
    process(conversations_path, out_dir)


if __name__ == '__main__':
    main()
