#!/usr/bin/env python
"""
extract_files.py

Walks conversations.json and extracts file contents from create_file
tool calls,.

Group output by conversation under:

    gen/<export-name>/extracted_files/<ordinal>-<slug>/<path_from_tool>

where <ordinal>-<slug> is the canonical conversation name from markdown_projection.ordered()
(created_at order, 1-based) — the same name used by the atomised json/, the timeline, and
lib/artifacts/downloaded/, so extracted files land beside their downloaded counterparts.

Usage:
    python extract_files.py --chat-export <path-to-export>
    python extract_files.py --chat-export <path> --out-dir <override-output-dir>
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import ordered


# ── extraction ────────────────────────────────────────────────────────────────

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

    log_path = out_dir / 'extract_files.log'
    skips: list[str] = []
    rows:  list[tuple] = []   # (ordinal, name, extracted, downloaded, copied)

    for idx, dir_name, convo in ordered(convos):  # canonical <ordinal>-<slug>, created_at order
        if idx is None:
            continue  # empty stub (nothing to extract)
        name     = convo['name']
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

        convo_dir = out_dir / dir_name
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
                dl_dest = dl_dir / rel
                dl_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, dl_dest)
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
        log.write(f'\nDone. {t_ext} extracted, {t_dl} already in downloaded, {t_cp} new (copied to {RSC_DIR.relative_to(SCRIPT_DIR.parents[2])} and {DOWNLOADED_DIR.relative_to(SCRIPT_DIR.parents[2])}).\n')


# ── main ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR     = Path(__file__).parent
OUTPUT_DIR     = SCRIPT_DIR.parent.parent.parent / 'gen' / 'chat-exports'
DOWNLOADED_DIR = SCRIPT_DIR.parent.parent.parent / 'lib' / 'artifacts' / 'downloaded'
RSC_DIR        = SCRIPT_DIR.parent.parent.parent / 'gen' / 'artifacts' / 'extracted_files'


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--chat-export', required=True)
    parser.add_argument('--out-dir',  default=None)
    args = parser.parse_args()

    data_dir           = Path(args.chat_export).resolve()
    conversations_path = data_dir / 'conversations.json'
    out_dir            = Path(args.out_dir) if args.out_dir else OUTPUT_DIR / data_dir.name / 'extracted_files'

    if not conversations_path.exists():
        sys.exit(f'conversations.json not found: {conversations_path}')

    out_dir.mkdir(parents=True, exist_ok=True)
    process(conversations_path, out_dir)


if __name__ == '__main__':
    main()
