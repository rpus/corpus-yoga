#!/usr/bin/env python
"""
survey_code_session.py — Survey the record types and field structure of one or more
Claude Code CLI session .jsonl files.

Useful for empirically grounding the code-agents schema before writing or
extending it, following the same approach as the conversations schema diagnostics.

Usage:
    python src/test/code-agents/survey_code_session.py ~/.claude/projects/{project-slug}/*.jsonl
    python src/test/code-agents/survey_code_session.py input/claude/code/machine-transport/{machine}/{project-slug}/*.jsonl

Output: a human-readable report to stdout covering:
  - Record counts per type across all files
  - All keys observed per type, with distinct values for discriminator-like fields
  - Content block types and tool names found in user/assistant turns
  - One sample record for each non-turn type
"""

import collections
import json
import sys
from pathlib import Path


def load_records(paths: list[Path]) -> list[dict]:
    records = []
    for p in paths:
        for line in p.read_text().splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def survey(records: list[dict]) -> None:
    by_type: dict[str, list[dict]] = collections.defaultdict(list)
    for r in records:
        by_type[r.get('type', '<missing>')].append(r)

    print(f'=== {len(records)} records total ===\n')

    # Per-type summary
    for rtype, recs in sorted(by_type.items(), key=lambda x: -len(x[1])):
        keys = sorted(set(k for r in recs for k in r))
        print(f'-- {rtype} (n={len(recs)}) --')
        print(f'   keys: {keys}')
        for field in ('operation', 'subtype', 'userType', 'isSidechain',
                      'isSnapshotUpdate', 'isApiErrorMessage', 'entrypoint',
                      'permissionMode', 'version'):
            vals = sorted(set(str(r.get(field)) for r in recs if field in r))
            if vals:
                print(f'   {field}: {vals}')
        print()

    # Content block summary for turns
    turns = [r for r in records if r.get('type') in ('user', 'assistant')]
    if turns:
        block_types: collections.Counter = collections.Counter()
        tool_names: collections.Counter = collections.Counter()
        for r in turns:
            for block in r.get('message', {}).get('content', []):
                bt = block.get('type')
                block_types[bt] += 1
                if bt == 'tool_use':
                    tool_names[block.get('name')] += 1
        print('=== content block types ===')
        for t, n in block_types.most_common():
            print(f'  {n:4d}  {t}')
        if tool_names:
            print('\n=== tool_use names ===')
            for t, n in tool_names.most_common():
                print(f'  {n:4d}  {t}')
        print()

    # Sample one record of each non-turn type
    sample_types = sorted(set(by_type) - {'user', 'assistant'})
    for rtype in sample_types:
        ex = by_type[rtype][0]
        print(f'=== sample: {rtype} ===')
        # Truncate long string values
        display = {k: (v[:120] if isinstance(v, str) and len(v) > 120 else v)
                   for k, v in ex.items()}
        print(json.dumps(display, indent=2))
        print()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    paths = [Path(p) for p in sys.argv[1:]]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f'Not found: {p}', file=sys.stderr)
        sys.exit(1)

    records = load_records(paths)
    survey(records)


if __name__ == '__main__':
    main()
