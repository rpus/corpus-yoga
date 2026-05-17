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
    schema     = pipeline.changelog.parent.name
    gen        = pipeline.gen
    new_format = bool(pipeline.dir_col and pipeline.uuid_col)
    if not gen.exists():
        sys.exit(f'{gen.relative_to(REPO_ROOT)} not found — run {pipeline.validate_cmd} ../{name} first')

    glob = (f'*/validation/{schema}/v*.log' if pipeline.subject_depth == 1
            else f'*/*/validation/{schema}/v*.log')

    # (subject, dir_name, uuid, version, symbol, bytes)
    rows: list[tuple[str, str, str, str, str, int]] = []
    for log in sorted(gen.glob(glob)):
        parts   = log.relative_to(gen).parts
        version = log.stem
        text    = log.read_text()
        _, nbytes = parse_size(text)
        if pipeline.subject_depth == 1:
            rows.append((f'`{parts[0]}`', '', '', version, result_symbol(text), nbytes or 0))
        elif new_format:
            dir_name = parts[0]
            uuid     = parts[1]
            abbrev   = dir_name.removeprefix(pipeline.slug_prefix)
            rows.append((f'`{abbrev}`', abbrev, uuid, version, result_symbol(text), nbytes or 0))
        else:
            part1 = parts[0].removeprefix(pipeline.gen_key_prefix)
            rows.append((f'`{part1}` / `{parts[1][:8]}`', '', '', version, result_symbol(text), nbytes or 0))

    versions = sorted({r[3] for r in rows}, key=lambda v: [int(x) for x in re.findall(r'\d+', v)])
    v_cols   = ' | '.join(f'[{v}](./{v}.json)' for v in versions)
    if new_format and pipeline.subject_depth == 2:
        out = [f'| {pipeline.dir_col} | {v_cols} | Bytes | {pipeline.uuid_col} |',
               '| --- | ' + ' | '.join(':---:' for _ in versions) + ' | ---: | --- |']
    else:
        out = [f'| {pipeline.subject_header} | {v_cols} | Bytes |',
               '| --- | ' + ' | '.join(':---:' for _ in versions) + ' | ---: |']

    by_uuid: dict[str, dict] = defaultdict(dict)  # uuid → {version: symbol, bytes, subject, dir_name}
    for subject, dir_name, uuid, version, symbol, nbytes in rows:
        key = uuid if uuid else subject
        by_uuid[key][version] = symbol
        by_uuid[key]['bytes']    = max(by_uuid[key].get('bytes', 0), nbytes)
        by_uuid[key]['subject']  = subject
        by_uuid[key]['dir_name'] = dir_name
        by_uuid[key]['uuid']     = uuid

    for key in sorted(by_uuid):
        d      = by_uuid[key]
        vcells = ' | '.join(d.get(v, '') for v in versions)
        if new_format and pipeline.subject_depth == 2:
            out.append(f'| {d["subject"]} | {vcells} | {d["bytes"]:,} | `{d["uuid"]}` |')
        else:
            out.append(f'| {d["subject"]} | {vcells} | {d["bytes"]:,} |')
    return out


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip('|').split('|')]


def _result_cells(row: str) -> list[str]:
    """Extract the ✓/✗/? result cells from a table row."""
    return [c for c in _cells(row) if c in ('✓', '✗', '?')]


def _uuid_from_row(row: str, uuid_col_idx: int | None) -> str | None:
    """Return the UUID cell value from a row, or None."""
    if uuid_col_idx is None:
        return None
    cells = _cells(row)
    if uuid_col_idx < len(cells):
        return cells[uuid_col_idx].replace('`', '').strip() or None
    return None


def _uuid_col_index(header_row: str) -> int | None:
    """Return the column index of the UUID column in a header row, or None."""
    cells = _cells(header_row)
    for i, c in enumerate(cells):
        if 'uuid' in c.lower():
            return i
    return None


def write_changelog(path: Path, new_table_lines: list[str], footer: str = '') -> None:
    """Update the generated block (matrix table + footer) in place.

    The block starts at <!-- matrix --> and ends just before the first --- separator.
    Everything before and after that block is preserved unchanged.

    For tables with a UUID column, rows are matched by UUID rather than col 1,
    so existing short repo/export names in col 1 are preserved when updating.
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

    new_header = new_table_lines[:2]

    # Determine match key: UUID column if present, otherwise col 1.
    new_uuid_col  = _uuid_col_index(new_table_lines[0]) if new_table_lines else None
    old_uuid_col  = _uuid_col_index(existing_table[0]) if existing_table else None

    def _key(row: str, uuid_col: int | None) -> str:
        uuid = _uuid_from_row(row, uuid_col)
        return uuid if uuid else re.sub(r'\s+', ' ', _cells(row)[0])

    new_by_key = {_key(r, new_uuid_col): r for r in new_table_lines[2:]}

    seen: set[str] = set()
    rewrites: list[tuple[str, str, str]] = []
    out = new_header[:]
    for row in existing_table[2:]:
        key = _key(row, old_uuid_col)
        new_row = new_by_key.get(key)
        if new_row is not None:
            # Preserve existing col 1 (human label) if the new row used the full dir name
            new_cells = _cells(new_row)
            old_cells = _cells(row)
            if old_uuid_col is not None and new_cells[0] != old_cells[0]:
                new_cells[0] = old_cells[0]
                new_row = '| ' + ' | '.join(new_cells) + ' |'
            if _result_cells(new_row) != _result_cells(row):
                rewrites.append((key, row.strip(), new_row.strip()))
        out.append(new_row if new_row is not None else row)
        seen.add(key)
    for key, row in sorted(new_by_key.items()):
        if key not in seen:
            out.append(row)

    if rewrites:
        print('ERROR: gen_changelog_matrix --write would rewrite existing history:', file=sys.stderr)
        for key, old, new in rewrites:
            print(f'  {key}', file=sys.stderr)
            print(f'    was: {old}', file=sys.stderr)
            print(f'    now: {new}', file=sys.stderr)
        print('Investigate the validation change before updating the CHANGELOG manually.', file=sys.stderr)
        sys.exit(1)

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
