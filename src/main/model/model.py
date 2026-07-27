#!/usr/bin/env python
"""
model.py — per-schema definition catalogues, candidates for rsc/schema/model.json.
Output: tmp/cache/model/{schema}/v{N}.json for each versioned schema (flat, not mirroring
rsc/schema/{pipeline}/{schema}/). rsc/schema/model.json is hand-curated from these.

`model` is a NOUN: the catalogues. A bare invocation shows their current state and
writes nothing (so there is no `status` verb — the bare noun IS the status). Only
the `sync` verb writes: it brings tmp/cache/model into agreement with the schemas, and
re-running is silence (L1) — which is what naming it `sync` promises.

Usage:
    yoga model         # status: which catalogues exist under tmp/cache/model/
    yoga model sync    # (re-)generate every catalogue to agree with the schemas
"""

import argparse
import re
import sys
from pathlib import Path

from gen_model_candidate import generate
from model_curation import (documented, rejected, edge_queue, orphan_entries,
                             coverage_gaps, unrecorded_collisions)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/ — modules both tiers import
from argparse_help import enrich  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT  = SCRIPT_DIR.parents[2]
SCHEMA_DIR = REPO_ROOT / 'rsc' / 'schema'
OUT_DIR    = REPO_ROOT / 'tmp' / 'cache' / 'model'


def _sorted_versions(schema_dir: Path) -> list[Path]:
    return sorted(
        schema_dir.glob('v*.json'),
        key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)]
    )


def _catalogues() -> list[tuple[str, Path]]:
    """(family, schema-version file) for every versioned schema — the inventory
    that `project` writes and `status` reports, so the two can never disagree."""
    out = []
    for pipeline_dir in sorted(SCHEMA_DIR.iterdir()):
        if not pipeline_dir.is_dir() or pipeline_dir.name.startswith('_'):
            continue
        for schema_dir in sorted(pipeline_dir.iterdir()):
            if not schema_dir.is_dir():
                continue
            for version in _sorted_versions(schema_dir):
                out.append((schema_dir.name, version))
    return out


def curation_report() -> None:
    """Both disposal loops, in numbers (issue #19; model_curation.py): the step
    that used to read 'update model.json if needed' now reports whether it IS
    needed. Loop 1 is leisurely (name collisions awaiting a model_join edge or a
    shrug — no gate pressure); loop 2 blocks (shared-type edges obligate
    model.json, gated per type by `yoga test run`'s check_model_obligations)."""
    queue = edge_queue()
    orphans = orphan_entries()
    gaps = coverage_gaps()
    print(f'rsc/schema/model.json — {len(documented())} documented · {len(rejected())} rejected · '
          f'{len(queue)} shared type(s) obligated by model_join and undisposed · '
          f'{len(orphans)} documented but ungrounded · {len(gaps)} documented incompletely'
          + (' (GATES)' if queue or orphans or gaps else ''))
    for names, rows in sorted(queue.items(), key=lambda kv: sorted(kv[0])):
        print(f'  ✗ {"/".join(sorted(names))} — model_join row(s) {", ".join(map(str, rows))}: '
              'document in rsc/schema/model.json | reject into rsc/schema/model_rejected.txt')
    for name in orphans:
        print(f'  ✗ {name} — documented with no grounding model_join edge: '
              'curate the asserting edge, or retire the entry')
    for name, fams in sorted(gaps.items()):
        print(f'  ✗ {name} — occurrences omit data famil(y/ies) its edge asserts: '
              f'{", ".join(fams)} — add the occurrence(s)')
    collisions = unrecorded_collisions()
    print(f'rsc/schema/model_join.csv — {len(collisions)} name collision(s) across families '
          'not yet recorded there (leisurely: curate an edge with its relationship kind, or ignore)')


def sync() -> None:
    """The verb: bring tmp/cache/model into agreement with the schemas by (re-)generating
    every catalogue. Idempotent (L1) — the ONLY path here that writes."""
    for name, schema in _catalogues():
        out_dir = OUT_DIR / name
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / schema.name).write_text(generate(name, schema))
        print(f'  ✓ tmp/cache/model/{name}/{schema.name}')
    curation_report()


def status() -> None:
    """The bare-noun default: show current state, write nothing. Reports which
    catalogues tmp/cache/model/ already holds and which a `project` would still
    mint, then the model.json disposal queue."""
    present, missing = [], []
    for name, schema in _catalogues():
        (present if (OUT_DIR / name / schema.name).exists() else missing).append(
            f'{name}/{schema.name}')
    total = len(present) + len(missing)
    print(f'tmp/cache/model: {len(present)}/{total} catalogues present')
    for m in missing:
        print(f'  – {m} — not yet projected')
    curation_report()


def main():
    ap = argparse.ArgumentParser(
        description='Per-schema definition catalogues (tmp/cache/model/<family>/vN.json), '
                    'candidates for the hand-curated rsc/schema/model.json. '
                    'Bare shows status; `sync` regenerates them to agree with the schemas.')
    sub = ap.add_subparsers(dest='verb')
    sub.add_parser('sync')
    enrich(ap, 'model')
    args = ap.parse_args()
    # bare → status (read-only); only `sync` writes
    sync() if args.verb == 'sync' else status()


if __name__ == '__main__':
    main()
