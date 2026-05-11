#!/usr/bin/env python
"""
gen_changelog_matrix.py — Update the CHANGELOG matrix from existing validation logs.

Reads gen/{pipeline}/ and rewrites the matrix table in the pipeline's CHANGELOG.md.
Run after validate.sh whenever a new batch or session has been validated.

Usage:
    src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline <pipeline>

Where <pipeline> is any key from PIPELINES in pre_commit.py.

Without --write, prints the new table to stdout instead of updating the file.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from pre_commit import Pipeline, PIPELINES, REPO_ROOT


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


CHANGELOGS = {name: p.changelog for name, p in PIPELINES.items()}


# ── Matrix generator ──────────────────────────────────────────────────────────

def gen_matrix(pipeline: Pipeline, name: str) -> list[str]:
    schema = pipeline.changelog.parent.name
    gen    = pipeline.gen
    if not gen.exists():
        sys.exit(f'{gen.relative_to(REPO_ROOT)} not found — run {pipeline.validate_cmd} ../{name} first')

    glob = (f'*/validation/{schema}/v*.log' if pipeline.subject_depth == 1
            else f'*/*/validation/{schema}/v*.log')

    rows: list[tuple[str, str, str, int]] = []  # (subject, version, symbol, bytes)
    for log in sorted(gen.glob(glob)):
        parts   = log.relative_to(gen).parts
        version = log.stem
        text    = log.read_text()
        _, nbytes = parse_size(text)
        if pipeline.subject_depth == 1:
            subject = f'`{parts[0]}`'
        else:
            part1   = parts[0].removeprefix(pipeline.gen_key_prefix)
            subject = f'`{part1}` / `{parts[1][:8]}`'
        rows.append((subject, version, result_symbol(text), nbytes or 0))

    versions = sorted({r[1] for r in rows}, key=lambda v: [int(x) for x in re.findall(r'\d+', v)])
    v_cols   = ' | '.join(f'[{v}](./{v}.json)' for v in versions)
    out = [f'| {pipeline.subject_header} | {v_cols} | Bytes |',
           '| --- | ' + ' | '.join(':---:' for _ in versions) + ' | ---: |']

    by_subject: dict[str, dict] = defaultdict(dict)
    for subject, version, symbol, nbytes in rows:
        by_subject[subject][version] = symbol
        by_subject[subject]['bytes'] = max(by_subject[subject].get('bytes', 0), nbytes)

    for subject in sorted(by_subject):
        d = by_subject[subject]
        vcells = ' | '.join(d.get(v, '') for v in versions)
        out.append(f'| {subject} | {vcells} | {d["bytes"]:,} |')
    return out


def _subject(row: str) -> str:
    return re.sub(r'\s+', ' ', row.split('|')[1].strip())


def write_changelog(path: Path, new_table_lines: list[str], footer: str = '') -> None:
    """Update the generated block (matrix table + footer) in place.

    The block starts at <!-- matrix --> and ends just before the first --- separator.
    Everything before and after that block is preserved unchanged.
    """
    if not path.exists() or '<!-- matrix -->' not in path.read_text():
        schema = path.parent.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'# {schema} schema changelog\n\n<!-- matrix -->\n\n---\n\n## v1\n\nInitial schema.\n')
        print(f'Created {path.relative_to(REPO_ROOT)}')

    text = path.read_text().splitlines()
    pre, existing_table, post = [], [], []
    in_block = past_block = False
    for line in text:
        if not past_block and not in_block and line.strip() == '<!-- matrix -->':
            pre.append(line)
            in_block = True
        elif in_block and line.startswith('---'):
            in_block = False
            past_block = True
            post.append(line)
        elif in_block:
            if line.startswith('|'):
                existing_table.append(line)
        elif past_block:
            post.append(line)
        else:
            pre.append(line)

    new_header  = new_table_lines[:2]
    new_by_subj = {_subject(r): r for r in new_table_lines[2:]}
    seen: set[str] = set()
    out = new_header[:]
    for row in existing_table[2:]:
        subj = _subject(row)
        out.append(new_by_subj[subj] if subj in new_by_subj else row)
        seen.add(subj)
    for subj, row in sorted(new_by_subj.items()):
        if subj not in seen:
            out.append(row)

    if footer:
        out += ['', footer]

    path.write_text('\n'.join(pre + out + [''] + post) + '\n')
    print(f'Updated {path.relative_to(REPO_ROOT)}')


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--pipeline', required=True,
                   choices=list(PIPELINES))
    p.add_argument('--write', action='store_true',
                   help='Update the CHANGELOG.md in place (default: print to stdout)')
    args = p.parse_args()

    pipeline = PIPELINES[args.pipeline]
    lines    = gen_matrix(pipeline, args.pipeline)

    if args.write:
        write_changelog(CHANGELOGS[args.pipeline], lines, pipeline.changelog_footer)
    else:
        print('\n'.join(lines))
        if pipeline.changelog_footer:
            print()
            print(pipeline.changelog_footer)


if __name__ == '__main__':
    main()
