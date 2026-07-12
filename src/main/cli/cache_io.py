#!/usr/bin/env python
"""
cache_io.py — the reader for rsc/cache_io.csv, the declared gen/ IO registry.

gen/ is the cache tier: every LIVE subtree is written and/or read by the
machinery. This registry declares, per gen/ subtree, WHO writes it (its
producer command) and WHO reads it (machinery consumers, or `external:<who>`
for a human/browser/shell). Paths are REPO-RELATIVE (`gen/…`), the real thing
you can cd to or rm. Three consumers share it:

  clean  — a gen/ subtree ABSENT from the registry is residue (neither written
           nor read): removable (yoga clean).
  regen  — the distinct producer commands rebuild gen/ (yoga regen).
  check  — pre_commit's check_cache_io blocks the catastrophe: a path READ with
           no WRITER (a gen/ dependency nothing produces) breaks the "gen/ is
           reproducible from ext/" contract. Written-but-not-read is fine (a
           terminal output — a page a browser reads); only the read side,
           lacking a writer, is fatal.

STDLIB-ONLY.
"""
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REGISTRY = REPO / 'rsc' / 'cache_io.csv'
COLUMNS = ('cache_path', 'pipeline', 'written_by', 'read_by', 'note')


def _split(cell: str) -> list[str]:
    return [x.strip() for x in cell.split(';') if x.strip()]


def rows() -> list[dict]:
    """The registry rows, each with parsed written_by / read_by lists. `pipeline`
    names the owning pipeline for a pipeline's gen root (empty for out-of-band
    producers). Raises if the columns drift — the registry is an interface."""
    with REGISTRY.open() as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f'{REGISTRY.relative_to(REPO)}: '
                             f'columns {reader.fieldnames} != {list(COLUMNS)}')
        out = []
        for r in reader:
            out.append({'cache_path': r['cache_path'].strip(),
                        'pipeline': r['pipeline'].strip(),
                        'written_by': _split(r['written_by']),
                        'read_by': _split(r['read_by']),
                        'note': r['note'].strip()})
        return out


def owned_paths() -> set[str]:
    """The repo-relative subtrees (`gen/…`) the machinery writes and/or reads —
    clean's keep-set; anything else on disk is residue."""
    return {r['cache_path'] for r in rows()}


def path_for(pipeline: str) -> str:
    """The repo-relative path (`gen/…`) a pipeline writes — the ONE authority for
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
    """The distinct producer commands, in first-seen order — regen's plan."""
    seen: list[str] = []
    for r in rows():
        for cmd in r['written_by']:
            if cmd not in seen:
                seen.append(cmd)
    return seen
