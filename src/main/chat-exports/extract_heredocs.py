#!/usr/bin/env python
"""
extract_heredocs.py

Walks conversations.json and extracts files written via heredoc inside
bash_tool commands, i.e. patterns of the form:

    cat > /some/path << 'EOF'
    ...content...
    EOF

Groups output by conversation under:

    gen/<export-name>/extracted_heredocs/<chat_index>_<conversation_name>/outputs/<filename>   ← /mnt/user-data/outputs/
    gen/<export-name>/extracted_heredocs/<chat_index>_<conversation_name>/working/<filename>   ← /home/claude/

Usage:
    python extract_heredocs.py --chat-export <path-to-export>
    python extract_heredocs.py --chat-export <path> --out-dir <override-output-dir>
"""

import argparse
import difflib
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
    rows: list[tuple] = []         # (idx, name, extracted, identical, newline_only, differs, copied)
    diff_entries: list[tuple] = [] # (chat_slug, rel, kind, diff_text|None)

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
        extracted = identical = newline_only = differs = copied = 0
        for e in by_path.values():
            dest = convo_dir / e['bucket'] / e['rel']
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(e['content'])
            extracted += 1

            if e['bucket'] == 'outputs':
                dl_path = DOWNLOADED_DIR / convo_dir.name / e['rel']
                if dl_path.exists():
                    dl_text = dl_path.read_text()
                    if dl_text == e['content']:
                        identical += 1
                    elif dl_text == e['content'] + '\n':
                        newline_only += 1
                        diff_entries.append((convo_dir.name, str(e['rel']), 'newline-only', 'download adds trailing newline'))
                    elif e['content'] == dl_text + '\n':
                        newline_only += 1
                        diff_entries.append((convo_dir.name, str(e['rel']), 'newline-only', 'download lacks trailing newline'))
                    else:
                        differs += 1
                        diff_lines = list(difflib.unified_diff(
                            e['content'].splitlines(keepends=True),
                            dl_text.splitlines(keepends=True),
                            fromfile=f'heredoc/{e["rel"]}',
                            tofile=f'downloaded/{e["rel"]}',
                        ))
                        diff_entries.append((convo_dir.name, str(e['rel']), 'differs', ''.join(diff_lines)))
                else:
                    rsc_dest = RSC_DIR / convo_dir.name / e['bucket'] / e['rel']
                    rsc_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, rsc_dest)
                    copied += 1
            else:
                dl_path = DOWNLOADED_DIR / convo_dir.name / e['bucket'] / e['rel']
                if dl_path.exists():
                    identical += 1
                else:
                    rsc_dest = RSC_DIR / convo_dir.name / e['bucket'] / e['rel']
                    rsc_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, rsc_dest)
                    copied += 1

        rows.append((idx, name[:50], extracted, identical, newline_only, differs, copied))

    with log_path.open('w') as log:
        if rows:
            nw = max(len(r[1]) for r in rows)
            hdr = f'  {"":3}  {"name":<{nw}}  {"extracted":>9}  {"identical":>9}  {"≈newline":>8}  {"↑differs":>8}  {"copied":>6}\n'
            sep = f'  {"":3}  {"-"*nw}  {"-"*9}  {"-"*9}  {"-"*8}  {"-"*8}  {"-"*6}\n'
            log.write(hdr + sep)
            for idx, name, extracted, identical, newline_only, differs, copied in rows:
                log.write(f'  {idx:03d}  {name:<{nw}}  {extracted:>9}  {identical:>9}  {newline_only:>8}  {differs:>8}  {copied:>6}\n')
            log.write(sep)
            t_ext  = sum(r[2] for r in rows)
            t_id   = sum(r[3] for r in rows)
            t_nl   = sum(r[4] for r in rows)
            t_diff = sum(r[5] for r in rows)
            t_cp   = sum(r[6] for r in rows)
            log.write(f'  {"":3}  {"TOTAL":<{nw}}  {t_ext:>9}  {t_id:>9}  {t_nl:>8}  {t_diff:>8}  {t_cp:>6}\n')
        else:
            t_ext = t_id = t_nl = t_diff = t_cp = 0
        log.write(f'\nDone. {t_ext} extracted: {t_id} identical, {t_nl} newline-only, {t_diff} ahead-in-downloaded, {t_cp} copied to rsc.\n')

        if diff_entries:
            log.write(f'\n── outputs/ files found in downloaded ({t_nl}+{t_diff}={t_nl+t_diff} shown, not copied to rsc) ──\n')
            for chat_slug, rel, kind, diff_text in diff_entries:
                if kind == 'newline-only':
                    log.write(f'  ≈ {chat_slug}/{rel}  ({diff_text} — not copied)\n')
                else:
                    log.write(f'  ↑ {chat_slug}/{rel}  (downloaded is ahead — not copied)\n')
                    for line in diff_text.splitlines():
                        log.write(f'    {line}\n')
                    log.write('\n')



SCRIPT_DIR     = Path(__file__).parent
OUTPUT_DIR     = SCRIPT_DIR.parent.parent.parent / 'gen' / 'chat-exports'
DOWNLOADED_DIR = SCRIPT_DIR.parent.parent.parent / 'rsc' / 'artifacts' / 'downloaded'
RSC_DIR        = SCRIPT_DIR.parent.parent.parent / 'rsc' / 'artifacts' / 'extracted_heredocs'


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
    out_dir            = Path(args.out_dir) if args.out_dir else OUTPUT_DIR / data_dir.name / 'extracted_heredocs'

    if not conversations_path.exists():
        sys.exit(f'Not found: {conversations_path}')

    out_dir.mkdir(parents=True, exist_ok=True)
    process(conversations_path, out_dir)


if __name__ == '__main__':
    main()
