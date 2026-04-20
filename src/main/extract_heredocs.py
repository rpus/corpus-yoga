#!/usr/bin/env python
"""
extract_heredocs.py

Walks conversations.json and extracts files written via heredoc inside
bash_tool commands, i.e. patterns of the form:

    cat > /some/path << 'EOF'
    ...content...
    EOF

Groups output by conversation under:

    <out_dir>/<chat_index>_<conversation_name>/outputs/<filename>   ← /mnt/user-data/outputs/
    <out_dir>/<chat_index>_<conversation_name>/working/<filename>   ← /home/claude/

Usage:
    python extract_heredocs.py --conversations conversations.json
    python extract_heredocs.py --conversations conversations.json --out-dir extracted_heredocs/
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

OUTPUTS_PREFIX = '/mnt/user-data/outputs/'
WORKING_PREFIX = '/home/claude/'

HEREDOC_RE = re.compile(
    r"cat\s*>\s*(\S+)\s*<<\s*'(\w+)'\n(.*?)\n\2",
    re.DOTALL
)


def slug(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '_', s)
    return s[:60].strip('_') or 'untitled'


def classify(raw_path: str) -> Optional[tuple[str, Path]]:
    """Return (bucket, relative_path) or None if unrecognised/unsafe."""
    if raw_path.startswith(OUTPUTS_PREFIX):
        rel = Path(raw_path[len(OUTPUTS_PREFIX):])
        bucket = 'outputs'
    elif raw_path.startswith(WORKING_PREFIX):
        rel = Path(raw_path[len(WORKING_PREFIX):])
        bucket = 'working'
    else:
        return None
    if rel.is_absolute() or '..' in rel.parts:
        return None
    return bucket, rel


def extract_from_command(command: str) -> list[dict]:
    results = []
    for m in HEREDOC_RE.finditer(command):
        raw_path, _delim, content = m.group(1), m.group(2), m.group(3)
        classified = classify(raw_path)
        if classified is None:
            continue
        bucket, rel = classified
        results.append({'bucket': bucket, 'rel': rel, 'content': content})
    return results


def process(conversations_path: Path, out_dir: Path) -> None:
    convos = json.loads(conversations_path.read_text())
    convos_sorted = sorted(convos, key=lambda c: c.get('created_at', ''))

    log_path = out_dir / 'extract_heredocs.log'
    rows: list[tuple] = []   # (idx, name, extracted, downloaded, copied)

    for idx, convo in enumerate(convos_sorted):
        name     = convo.get('name', 'untitled')
        messages = convo.get('chat_messages', [])

        # Collect heredocs; last write for each bucket/path wins
        by_path: dict[str, dict] = {}
        for msg in messages:
            for block in msg.get('content', []):
                if block.get('type') != 'tool_use' or block.get('name') != 'bash_tool':
                    continue
                command = block.get('input', {}).get('command', '')
                for e in extract_from_command(command):
                    by_path[f"{e['bucket']}/{e['rel']}"] = e

        if not by_path:
            continue

        convo_dir = out_dir / f'{idx:03d}_{slug(name)}'
        extracted = downloaded = copied = 0
        for e in by_path.values():
            dest = convo_dir / e['bucket'] / e['rel']
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(e['content'])
            extracted += 1
            dl_dir = DOWNLOADED_DIR / convo_dir.name
            if dl_dir.exists() and list(dl_dir.rglob(e['rel'].name)):
                downloaded += 1
            else:
                rsc_dest = RSC_DIR / convo_dir.name / e['bucket'] / e['rel']
                rsc_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, rsc_dest)
                copied += 1

        rows.append((idx, name[:50], extracted, downloaded, copied))

    with log_path.open('w') as log:
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
        log.write(f'\nDone. {t_ext} extracted, {t_dl} already downloaded, {t_cp} copied to rsc.\n')



SCRIPT_DIR     = Path(__file__).parent
OUTPUT_DIR     = SCRIPT_DIR.parent.parent / 'gen'
DOWNLOADED_DIR = SCRIPT_DIR.parent.parent / 'rsc' / 'artifacts' / 'downloaded'
RSC_DIR        = SCRIPT_DIR.parent.parent / 'rsc' / 'artifacts' / 'extracted_heredocs'


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--conversations', default=None)
    parser.add_argument('--data-dir',      default=None)
    parser.add_argument('--out-dir',       default=None)
    args = parser.parse_args()

    if args.data_dir:
        data_dir           = Path(args.data_dir).resolve()
        conversations_path = data_dir / 'conversations.json'
        out_dir            = Path(args.out_dir) if args.out_dir else OUTPUT_DIR / data_dir.name / 'extracted_heredocs'
    else:
        conversations_path = Path(args.conversations or 'conversations.json')
        out_dir            = Path(args.out_dir or 'extracted_heredocs')

    if not conversations_path.exists():
        sys.exit(f'Not found: {conversations_path}')

    out_dir.mkdir(parents=True, exist_ok=True)
    process(conversations_path, out_dir)


if __name__ == '__main__':
    main()
