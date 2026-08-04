#!/usr/bin/env python
"""
validation_matrix.py — render a datum's machine-local validation matrix from its logs.

Each datum directory under tmp/cache/ whose validation/ holds vN.log files gets a single
sibling matrix.md summarising them (schema × version → ✓/✗, bytes). The matrix is
derived state: git-ignored, co-located with its datum, and written by validation
itself (validate_versions.py) whenever the logs change — so it can never be stale.
src/test/dev/gen_changelog_matrix.py re-renders or aggregates without revalidating.
"""

import os
import re
from pathlib import Path

PREAMBLE = """# validation matrix

Machine-local (git-ignored): which schema versions this datum validates against,
derived from the vN.log files under validation/ at validation time.
The version narrative lives in the committed CHANGELOG.md beside each schema.
"""

HEADER = ['| Schema | Item | Version | Result | Bytes |',
          '| --- | --- | :---: | :---: | ---: |']


def result_symbol(log_text: str) -> str:
    if 'Valid!' in log_text:
        return '✓'
    if 'Validation error' in log_text:
        return '✗'
    return '?'


def log_bytes(log_text: str) -> int:
    m = re.search(r': (?:\d+ lines, )?(\d+) bytes', log_text)
    return int(m.group(1)) if m else 0


def rows_from_logs(datum_dir: Path) -> dict[tuple[str, str, str], tuple[str, int]]:
    """(schema, item, version) → (✓/✗/?, bytes) from the vN.log files under one datum's
    validation/ directory. `item` is the inner subject for nested layouts (chat-exports
    projects), '' otherwise. This is the source of truth the datum's matrix.md renders."""
    rows: dict[tuple[str, str, str], tuple[str, int]] = {}
    vdir = datum_dir / 'validation'
    if not vdir.is_dir():
        return rows
    for schema_dir in sorted(d for d in vdir.iterdir() if d.is_dir()):
        schema = schema_dir.name
        for entry in sorted(schema_dir.iterdir()):
            if entry.is_file() and re.fullmatch(r'v\d+\.log', entry.name):
                text = entry.read_text()
                rows[(schema, '', entry.stem)] = (result_symbol(text), log_bytes(text))
            elif entry.is_dir():
                for log in sorted(entry.glob('v*.log')):
                    text = log.read_text()
                    rows[(schema, entry.name, log.stem)] = (result_symbol(text), log_bytes(text))
    return rows


def _row_sort_key(key):
    schema, item, version = key
    return (schema, item, [int(x) for x in re.findall(r'\d+', version)])


def render_rows(datum_dir: Path, schema_parent_dir: Path) -> list[str]:
    """One table row per (schema, item, version) found under datum_dir/validation/.
    schema_parent_dir is the rsc/schema/<pipeline>/ directory the version links target."""
    rows = rows_from_logs(datum_dir)
    out = []
    for key in sorted(rows, key=_row_sort_key):
        schema, item, version = key
        symbol, nbytes = rows[key]
        vfile     = schema_parent_dir / schema / f'{version}.json'
        rel       = os.path.relpath(vfile, datum_dir)
        item_cell = f'`{item}`' if item else ''
        out.append(f'| {schema} | {item_cell} | [{version}]({rel}) | {symbol} | {nbytes:,} |')
    return out


def write_matrix(datum_dir: Path, schema_parent_dir: Path) -> Path | None:
    """Write (or rewrite) datum_dir/matrix.md. Returns its path, or None if no logs."""
    body = render_rows(datum_dir, schema_parent_dir)
    if not body:
        return None
    mfile = datum_dir / 'matrix.md'
    mfile.write_text(PREAMBLE + '\n' + '\n'.join(HEADER + body) + '\n')
    return mfile


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        sys.exit(f'Usage: {sys.argv[0]} <datum_dir> <rsc_schema_pipeline_dir>')
    out = write_matrix(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    if out:
        print(f'  matrix: {out}')
