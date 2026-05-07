#!/usr/bin/env python
"""
gen_changelog_matrix.py — Generate CHANGELOG matrix rows from existing validation logs.

Reads gen/{pipeline}/ and emits markdown table rows ready to paste into the
pipeline's CHANGELOG.md. Run after validate.sh to record a new batch or session.

Usage:
    src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline chat-exports
    src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline code-projects
    src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline browser-captures
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT       = Path(__file__).resolve().parents[2]
GEN             = REPO_ROOT / 'gen'
_PROJECT_PREFIX = str(REPO_ROOT.parent).replace('/', '-') + '-'


def result_symbol(log_text: str) -> str:
    if 'Valid!' in log_text:
        return '✓'
    if 'Validation error' in log_text:
        return '✗'
    return '?'


def parse_size(log_text: str) -> tuple[int | None, int | None]:
    """Return (lines, bytes) from the input-file line of a log, or (None, None)."""
    m = re.search(r': (\d+) lines, (\d+) bytes', log_text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r': (\d+) bytes', log_text)
    if m:
        return None, int(m.group(1))
    return None, None


# ── chat-exports ──────────────────────────────────────────────────────────────

def gen_chat_exports():
    gen = GEN / 'chat-exports'
    if not gen.exists():
        sys.exit(f'gen/chat-exports/ not found — run validate.sh first')

    # Collect {data_dir: {version: symbol}}
    matrix: dict[str, dict[str, str]] = defaultdict(dict)
    versions_seen: set[str] = set()

    for log in sorted(gen.glob('*/validation/conversations/v*.log')):
        data_dir = log.parts[log.parts.index('chat-exports') + 1]
        version  = log.stem
        matrix[data_dir][version] = result_symbol(log.read_text())
        versions_seen.add(version)

    versions = sorted(versions_seen, key=lambda v: [int(x) for x in re.findall(r'\d+', v)])
    header   = '| Export | ' + ' | '.join(f'[{v}](./conversations/{v}.json)' for v in versions) + ' |'
    sep      = '| --- | ' + ' | '.join(':---:' for _ in versions) + ' |'

    print(header)
    print(sep)
    for data_dir in sorted(matrix):
        cells = ' | '.join(matrix[data_dir].get(v, '') for v in versions)
        print(f'| `{data_dir}` | {cells} |')


# ── code-projects ─────────────────────────────────────────────────────────────

def gen_code_projects():
    gen = GEN / 'code-projects'
    if not gen.exists():
        sys.exit(f'gen/code-projects/ not found — run RUNME.sh first')

    rows: list[tuple[str, str, str, int, int]] = []  # (subject, version, symbol, lines, bytes)

    for log in sorted(gen.glob('*/*/validation/session/v*.log')):
        parts       = log.relative_to(gen).parts
        project_dir = parts[0]
        session_dir = parts[1]
        version     = log.stem
        project     = project_dir.removeprefix(_PROJECT_PREFIX)
        prefix      = session_dir[:8]
        subject     = f'`{project}` / `{prefix}`'
        text        = log.read_text()
        symbol      = result_symbol(text)
        lines, nbytes = parse_size(text)
        rows.append((subject, version, symbol, lines or 0, nbytes or 0))

    # Collect all versions
    versions = sorted({r[1] for r in rows}, key=lambda v: [int(x) for x in re.findall(r'\d+', v)])
    v_cols   = ' | '.join(f'[{v}](./{v}.json)' for v in versions)
    print(f'| Session | {v_cols} | Lines | Bytes (JSONL) |')
    print(f'| --- | ' + ' | '.join(':---:' for _ in versions) + ' | ---: | ---: |')

    # Group by subject
    by_subject: dict[str, dict] = defaultdict(dict)
    for subject, version, symbol, lines, nbytes in rows:
        by_subject[subject][version]  = symbol
        by_subject[subject]['lines']  = lines
        by_subject[subject]['bytes']  = nbytes

    for subject in sorted(by_subject):
        d      = by_subject[subject]
        vcells = ' | '.join(d.get(v, '') for v in versions)
        lines  = f'{d["lines"]:,}'
        nbytes = f'{d["bytes"]:,}'
        print(f'| {subject} | {vcells} | {lines} | {nbytes} |')


# ── browser-captures ──────────────────────────────────────────────────────────

def gen_browser_captures():
    gen = GEN / 'browser-captures'
    if not gen.exists():
        sys.exit(f'gen/browser-captures/ not found — run validate.sh first')

    rows: list[tuple[str, str, str, int]] = []  # (subject, version, symbol, bytes)

    for log in sorted(gen.glob('*/*/validation/apiConversation/v*.log')):
        parts    = log.relative_to(gen).parts
        batch    = parts[0]
        conv     = parts[1]
        version  = log.stem
        text     = log.read_text()
        symbol   = result_symbol(text)
        _, nbytes = parse_size(text)
        subject  = f'`{batch}` / `{conv[:8]}`'
        rows.append((subject, version, symbol, nbytes or 0))

    versions = sorted({r[1] for r in rows}, key=lambda v: [int(x) for x in re.findall(r'\d+', v)])
    v_cols   = ' | '.join(f'[{v}](./apiConversation/{v}.json)' for v in versions)
    print(f'| Export / Conversation | {v_cols} | Bytes (JSON) |')
    print(f'| --- | ' + ' | '.join(':---:' for _ in versions) + ' | ---: |')

    by_subject: dict[str, dict] = defaultdict(dict)
    for subject, version, symbol, nbytes in rows:
        by_subject[subject][version] = symbol
        by_subject[subject]['bytes'] = nbytes

    for subject in sorted(by_subject):
        d      = by_subject[subject]
        vcells = ' | '.join(d.get(v, '') for v in versions)
        nbytes = f'{d["bytes"]:,}'
        print(f'| {subject} | {vcells} | {nbytes} |')


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--pipeline', required=True,
                   choices=['chat-exports', 'code-projects', 'browser-captures'])
    args = p.parse_args()

    {'chat-exports':     gen_chat_exports,
     'code-projects':    gen_code_projects,
     'browser-captures': gen_browser_captures}[args.pipeline]()


if __name__ == '__main__':
    main()
