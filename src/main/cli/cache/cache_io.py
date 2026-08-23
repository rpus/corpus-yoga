#!/usr/bin/env python
"""
cache_io.py — the reader for rsc/cache_io.csv, the declared tmp/cache/ IO registry.

tmp/cache/ is the cache tier: every LIVE subtree is written and/or read by the
machinery. This registry declares, per tmp/cache/ subtree, WHO writes it (its
producer command) and WHO reads it (machinery consumers, or `external:<who>`
for a human/browser/shell). Paths are REPO-RELATIVE (`tmp/cache/…`), the real thing
you can cd to or rm. Three consumers share it:

  clean  — a tmp/cache/ subtree ABSENT from the registry is residue (neither written
           nor read): removable (corpus-yoga cache clean).
  sync   — every row's producer commands rebuild tmp/cache/ (corpus-yoga cache sync).
  check  — `corpus-yoga test run`'s check_cache_io blocks the catastrophe: a path READ with
           no WRITER (a tmp/cache/ dependency nothing produces) breaks the "tmp/cache/ is
           reproducible from data/input/" contract. Written-but-not-read is fine (a
           terminal output — a page a browser reads); only the read side,
           lacking a writer, is fatal.

STDLIB-ONLY.
"""
import csv
from pathlib import Path

SELF = 'src/main/cli/cache/cache_io.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
REGISTRY = REPO / 'rsc' / 'cache_io.csv'
COLUMNS = ('cache_path', 'pipeline', 'written_by', 'read_by', 'note')


def _split(cell: str) -> list[str]:
    return [x.strip() for x in cell.split(';') if x.strip()]


def rows() -> list[dict]:
    """The registry rows, each with parsed written_by / read_by lists. `pipeline`
    names the owning pipeline for a pipeline's cache root (empty for out-of-band
    producers). Raises if the columns drift, or a row's field count isn't exactly
    len(COLUMNS) — an unquoted comma in a cell would otherwise silently truncate the
    note into csv's overflow. The registry is an interface."""
    with REGISTRY.open() as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f'{REGISTRY.relative_to(REPO)}: '
                             f'columns {reader.fieldnames} != {list(COLUMNS)}')
        out = []
        for n, r in enumerate(reader, start=2):  # file line 1 is the header
            overflow = r.get(None)  # csv.DictReader dumps surplus cells here
            if overflow:
                raise ValueError(
                    f'{REGISTRY.relative_to(REPO)} row {n} ({r[COLUMNS[0]]!r}): '
                    f'{len(COLUMNS) + len(overflow)} fields, expected {len(COLUMNS)} — '
                    f'an unquoted comma in a cell? surplus: {overflow}')
            missing = [c for c in COLUMNS if r[c] is None]
            if missing:
                raise ValueError(
                    f'{REGISTRY.relative_to(REPO)} row {n} ({r[COLUMNS[0]]!r}): '
                    f'fewer than {len(COLUMNS)} fields — missing {missing}')
            out.append({'cache_path': r['cache_path'].strip(),
                        'pipeline': r['pipeline'].strip(),
                        'written_by': _split(r['written_by']),
                        'read_by': _split(r['read_by']),
                        'note': r['note'].strip()})
        return out


def owned_paths() -> set[str]:
    """The repo-relative subtrees (`tmp/cache/…`) the machinery writes and/or reads —
    clean's keep-set; anything else on disk is residue."""
    return {r['cache_path'] for r in rows()}


def path_for(pipeline: str) -> str:
    """The repo-relative path (`tmp/cache/…`) a pipeline writes — the ONE authority for
    it, so PIPELINES derives its cache_output from here rather than restating it.
    Raises loudly if a pipeline has no row (a pipeline unbuildable without its
    cache_io declaration is the point)."""
    matches = [r['cache_path'] for r in rows() if r['pipeline'] == pipeline]
    if len(matches) != 1:
        raise ValueError(f'{REGISTRY.name}: pipeline {pipeline!r} has {len(matches)} rows, expected 1')
    return matches[0]


def pipelines() -> set[str]:
    """The pipeline names the registry tags — cross-checked against PIPELINES."""
    return {r['pipeline'] for r in rows() if r['pipeline']}


def producers() -> list[str]:
    """Every written_by command, row by row in registry order — sync's plan.
    Deliberately NO dedup: the row is the unit of the reproduction claim, and a
    command string shared by two rows proves nothing about one run covering
    both — a producer may write more than its row declares (site render
    also lands the data/output/ page) or less than a twin row hopes. A shared
    command running twice is the safe reading."""
    cmds: list[str] = []
    for r in rows():
        cmds.extend(r['written_by'])
    return cmds
