#!/usr/bin/env python
"""
extract_heredocs.py

Walks conversations.json and extracts files written via heredoc inside
bash_tool commands, i.e. patterns of the form:

    cat > /some/path << 'EOF'
    ...content...
    EOF

Groups output by conversation under:

    gen/<export-name>/extracted_heredocs/<ordinal>-<slug>/outputs/<filename>   ← /mnt/user-data/outputs/
    gen/<export-name>/extracted_heredocs/<ordinal>-<slug>/working/<filename>   ← /home/claude/

where <ordinal>-<slug> is the canonical conversation name from markdown_projection.ordered().
The durable library lib/artifacts/downloaded/ is keyed by identity instead (<uuid8>-<slug>,
resolved via library.py); files new to the library are copied there and echoed to the
gen/artifacts delta log under the library's directory name.

Usage:
    python extract_heredocs.py --chat-export <path-to-export>
    python extract_heredocs.py --chat-export <path> --out-dir <override-output-dir>
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import ordered
from library import dir_for, LIBRARY

OUTPUTS_PREFIX = '/mnt/user-data/outputs/'
WORKING_PREFIX = '/home/claude/'

HEREDOC_RE = re.compile(
    r"cat\s*>\s*(\S+)\s*<<\s*'(\w+)'\n(.*?)\n\2",
    re.DOTALL
)


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

    if out_dir.exists():
        shutil.rmtree(out_dir)  # renumbering renames per-conversation dirs; wipe so no old-naming dirs linger
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / 'extract_heredocs.log'
    rows: list[tuple] = []         # (ordinal, name, extracted, identical, newline_only, differs, copied)
    diff_entries: list[tuple] = [] # (chat_slug, rel, kind, diff_text|None)

    for idx, dir_name, convo in ordered(convos):  # canonical <ordinal>-<slug>, created_at order
        if idx is None:
            continue  # empty stub (nothing to extract)
        name     = convo['name']
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

        convo_dir = out_dir / dir_name
        # library resolution is by uuid (identity), never by the batch ordinal name
        dl_dir = dir_for(convo['uuid'], dir_name.split('-', 1)[1])
        extracted = identical = newline_only = differs = copied = 0
        for e in by_path.values():
            dest = convo_dir / e['bucket'] / e['rel']
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(e['content'])
            extracted += 1

            if e['bucket'] == 'outputs':
                dl_path = dl_dir / e['rel']
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
                        diff_entries.append((convo_dir.name, str(e['rel']), 'differs',
                                             dest, dl_path))
                else:
                    rsc_dest = RSC_DIR / dl_dir.name / e['bucket'] / e['rel']
                    rsc_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, rsc_dest)
                    dl_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, dl_path)
                    copied += 1
            else:
                # working/ files (/home/claude/) are internal to the Claude sandbox and cannot
                # be downloaded from the claude.ai UI, so there is no user-downloaded version
                # to diff against. Existence check only.
                dl_path = dl_dir / e['bucket'] / e['rel']
                if dl_path.exists():
                    identical += 1
                else:
                    rsc_dest = RSC_DIR / dl_dir.name / e['bucket'] / e['rel']
                    rsc_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, rsc_dest)
                    dl_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, dl_path)
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
        log.write(f'\nDone. {t_ext} extracted: {t_id} identical, {t_nl} newline-only, {t_diff} ahead-in-downloaded, {t_cp} new (copied to {RSC_DIR.relative_to(SCRIPT_DIR.parents[2])} and {LIBRARY.relative_to(SCRIPT_DIR.parents[2])}).\n')

        if diff_entries:
            log.write(f'\n── outputs/ files found in downloaded ({t_nl}+{t_diff}={t_nl+t_diff} shown, not copied to {RSC_DIR.relative_to(SCRIPT_DIR.parents[2])}) ──\n')
            for entry in diff_entries:
                chat_slug, rel, kind = entry[0], entry[1], entry[2]
                if kind == 'newline-only':
                    log.write(f'  ≈ {chat_slug}/{rel}  ({entry[3]} — not copied)\n')
                else:
                    extracted_path, dl_path_arg = entry[3], entry[4]
                    log.write(f'  ↑ {chat_slug}/{rel}  (downloaded is ahead — not copied)\n')
                    log.write(f'    diff {extracted_path} {dl_path_arg}\n')


SCRIPT_DIR     = Path(__file__).parent
OUTPUT_DIR     = SCRIPT_DIR.parent.parent.parent / 'gen' / 'chat-exports'
RSC_DIR        = SCRIPT_DIR.parent.parent.parent / 'gen' / 'artifacts' / 'extracted_heredocs'


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
