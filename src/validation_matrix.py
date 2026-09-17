#!/usr/bin/env python
"""
validation_matrix.py — render a datum's machine-local validation matrix from its logs.

Each datum directory under tmp/cache/ whose validation/ holds vN.log files gets a single
sibling matrix.md summarising them (schema × version → ✓/✗, bytes). The matrix is
derived state: git-ignored, co-located with its datum, and written by validation
itself (validate_versions.py) whenever the logs change — so it can never be stale.
src/test/dev/gen_changelog_matrix.py re-renders or aggregates without revalidating;
src/main/validation_audit.py judges the logs and matrices (corpus-yoga pipeline audit).
"""

import json
import os
import re
from pathlib import Path

PREAMBLE = """# validation matrix

Machine-local (git-ignored): whether this datum validates at each family's latest
version, derived from that version's log under validation/ at validation time.
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


def family_dir(root: Path, schema: str, datum_dir: Path | None = None) -> Path | None:
    """The one address of a family under a pipeline's schema root, rsc/schema/pipeline/<pipeline>
    (#632): directly, or at the provider's segment where the family's instances are one
    provider's. A pipeline's declaration (src/main/pipeline/<pipeline>/pipeline.json,
    `schemas`) names its families by address, and the one whose last segment is schema is
    the family; a family the declaration does not name is found by walking. None where
    neither gives exactly one."""
    declaration = root.parents[3] / 'src' / 'main' / 'pipeline' / root.name / 'pipeline.json'
    declared = json.loads(declaration.read_text())['schemas'] if declaration.is_file() else []
    named = [root / a for a in declared if a.rsplit('/', 1)[-1] == schema]
    if len(named) > 1 and datum_dir is not None:
        # two providers' families of one name (#635): the datum sits under its provider's
        # directory of the cache, tmp/cache/<pipeline>/<provider>/..., and the family under
        # the same segment of the schema root - that one segment, never any component, or a
        # machine or project named for a provider would match both
        parts = datum_dir.parts
        under = [parts[i + 2] for i in range(len(parts) - 2) if parts[i:i + 2] == ('cache', root.name)]
        named = [f for f in named if under and f.relative_to(root).parts[0] == under[-1]]
    hits = named or [d for d in sorted(root.glob(schema)) + sorted(root.glob(f'*/{schema}'))
                     if d.is_dir() and list(d.glob('v*.json'))]
    return hits[0] if len(hits) == 1 else None


def family_root(schema_dir: Path) -> Path:
    """The schema root a family's matrix resolves its siblings against: for a pipeline's
    family, rsc/schema/pipeline/<pipeline>, the directory directly under rsc/schema/pipeline
    on its path; for any other family, its parent."""
    for p in schema_dir.parents:
        if p.parent.name == 'pipeline' and p.parent.parent.name == 'schema':
            return p
    return schema_dir.parent


def latest_version(schema_parent_dir: Path, schema: str, datum_dir: Path | None = None) -> str | None:
    """The family's latest version stem (vN), by numeric order; None if it has none."""
    d = family_dir(schema_parent_dir, schema, datum_dir)
    if d is None:
        return None
    versions = sorted(d.glob('v*.json'), key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)])
    return versions[-1].stem if versions else None


def rows_from_logs(datum_dir: Path, schema_parent_dir: Path) -> dict[tuple[str, str, str], tuple[str, int]]:
    """(schema, item, latest version) → (✓/✗/?, bytes) from the LATEST version's log under
    one datum's validation/ directory - the latest version is the schema, the rest is
    history (#557), so an older vN.log left beside it is not a row. `item` is the inner
    subject for nested layouts (chat-export projects), '' otherwise. This is the source
    of truth the datum's matrix.md renders."""
    rows: dict[tuple[str, str, str], tuple[str, int]] = {}
    vdir = datum_dir / 'validation'
    if not vdir.is_dir():
        return rows
    for schema_dir in sorted(d for d in vdir.iterdir() if d.is_dir()):
        schema = schema_dir.name
        latest = latest_version(schema_parent_dir, schema, datum_dir)
        if latest is None:
            continue
        direct = schema_dir / f'{latest}.log'
        if direct.is_file():
            text = direct.read_text()
            rows[(schema, '', latest)] = (result_symbol(text), log_bytes(text))
        for entry in sorted(schema_dir.iterdir()):
            if entry.is_dir() and (entry / f'{latest}.log').is_file():
                text = (entry / f'{latest}.log').read_text()
                rows[(schema, entry.name, latest)] = (result_symbol(text), log_bytes(text))
    return rows


def _row_sort_key(key):
    schema, item, version = key
    return (schema, item, [int(x) for x in re.findall(r'\d+', version)])


def render_rows(datum_dir: Path, schema_parent_dir: Path) -> list[str]:
    """One table row per (schema, item, version) found under datum_dir/validation/.
    schema_parent_dir is the schema root (family_root) the version links resolve under."""
    rows = rows_from_logs(datum_dir, schema_parent_dir)
    out = []
    for key in sorted(rows, key=_row_sort_key):
        schema, item, version = key
        symbol, nbytes = rows[key]
        fam       = family_dir(schema_parent_dir, schema, datum_dir)
        assert fam is not None, f'{schema}: no family under {schema_parent_dir}'   # rows_from_logs admitted it
        vfile     = fam / f'{version}.json'
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
        sys.exit(f'Usage: {sys.argv[0]} <datum_dir> <schema_root>   # rsc/schema/pipeline/<pipeline>')
    out = write_matrix(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    if out:
        print(f'  matrix: {out}')
