#!/usr/bin/env python
"""
extract_files.py

Walks conversations.json and extracts file contents from create_file
tool calls,.

Group output by conversation under:

    tmp/cache/<export-name>/extracted_files/<ordinal>-<slug>/<path_from_tool>

where <ordinal>-<slug> is the canonical conversation name from markdown_projection.ordered()
(created_at order, 1-based) — the same name used by the atomised json/ and the timeline.
The durable library data/output/artifacts/downloaded/ is keyed by identity instead
(<ordinal>-<slug>-<uuid8>, resolved via src/main/chat-exports/library.py — ordinals renumber
between batches, uuids don't); files new to the library are copied there and named
individually in this run's log (the delta is information, not a second copy).

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
from library import assert_uuid8_unique, dir_for, LIBRARY


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
    assert_uuid8_unique(c['uuid'] for c in convos)  # dir_for keys by uuid8; verify before minting

    if out_dir.exists():
        shutil.rmtree(out_dir)  # renumbering renames per-conversation dirs; wipe so no old-naming dirs linger
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / 'extract_files.log'
    skips: list[str] = []
    new_copies: list[str] = []   # files this run added to the library (the delta)
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
        # library resolution is by uuid (identity); the batch's canonical name is
        # passed as dressing, refreshed onto the dir so listings track current numbering
        dl_dir = dir_for(convo['uuid'], dir_name)
        extracted = downloaded = copied = 0
        for entry in by_path.values():
            rel = entry['rel']
            dest = convo_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(entry['file_text'])
            extracted += 1
            if (dl_dir / rel).exists():
                downloaded += 1
            else:
                dl_dest = dl_dir / rel
                dl_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, dl_dest)
                copied += 1
                new_copies.append(f'  NEW→library {dl_dir.name}/{rel}')

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
        log.write(f'\nDone. {t_ext} extracted, {t_dl} already in downloaded, {t_cp} new (copied to {LIBRARY.relative_to(SCRIPT_DIR.parents[2])}).\n')
        if new_copies:
            log.write('\n'.join(new_copies) + '\n')


# ── main ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR     = Path(__file__).parent
CACHE_DIR     = SCRIPT_DIR.parent.parent.parent / 'tmp' / 'cache' / 'chat-exports'


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
    out_dir            = Path(args.out_dir) if args.out_dir else CACHE_DIR / data_dir.name / 'extracted_files'

    if not conversations_path.exists():
        sys.exit(f'conversations.json not found: {conversations_path}')

    out_dir.mkdir(parents=True, exist_ok=True)
    process(conversations_path, out_dir)


if __name__ == '__main__':
    main()
