#!/usr/bin/env python
"""
mcp.py - the house factoring of the MCP schema, rsc/schema/protocol/mcpMessage,
derived from the two committed upstream files under rsc/reference/mcp: schema.ts,
whose extends clauses and type aliases mcp_extraction.py reads (#581), and
schema.json, the snapshot every definition is verified against.

`mcp` is a NOUN: the derived schema. A bare invocation shows its state and writes
nothing (the bare noun IS the status). Only `sync` writes: the two extracted
tables under tmp/cache/mcp/ (the readable face of the derivation's inputs) and the
family's latest version file, and re-running is silence (L1). The witness that the derivation preserved meaning is the dev gate's
(mcp.factoring_agrees); the currency of the committed file is its too
(mcp.factoring_current).

Usage:
    corpus-yoga mcp              # status: is rsc/schema/protocol/mcpMessage current with the snapshot?
    corpus-yoga mcp sync         # (re-)derive the latest rsc/schema/protocol/mcpMessage/v*.json - idempotent
    corpus-yoga mcp reproduce    # is the snapshot's schema.json what upstream's generator makes of its
                                 # schema.ts? - src/main/mcp/reproduce.sh, whose header states the run
"""

import json
import os
import sys
from pathlib import Path

SELF = 'src/main/mcp/mcp.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))  # src/ — modules both tiers import
from declared_parser import command_parser  # noqa: E402

import mcp_factoring as factoring  # noqa: E402  (sibling module)


def _target() -> Path:
    latest = factoring.latest_version(factoring.FAMILY_DIR)
    return latest if latest else factoring.FAMILY_DIR / 'v1.json'


def _tables_current(declared: dict, rows: list) -> bool:
    """Whether tmp/cache/mcp/ holds the tables as extracted now."""
    import tempfile
    with tempfile.TemporaryDirectory() as scratch:
        saved = factoring.CACHE_DIR, factoring.COMPOSITION, factoring.ALIASES
        try:
            factoring.CACHE_DIR = Path(scratch)
            factoring.COMPOSITION = factoring.CACHE_DIR / 'composition.csv'
            factoring.ALIASES = factoring.CACHE_DIR / 'alias.csv'
            fresh = {p.name: p.read_text() for p in factoring.written_tables(declared, rows)}
        finally:
            factoring.CACHE_DIR, factoring.COMPOSITION, factoring.ALIASES = saved
    return all((factoring.CACHE_DIR / name).is_file() and (factoring.CACHE_DIR / name).read_text() == text
               for name, text in fresh.items())


def status() -> int:
    target = _target()
    rel = target.relative_to(REPO)
    snapshot_path, snap = factoring.snapshot()
    shapes, declared, rows = factoring.inputs()
    wanted = factoring.rendered(factoring.factored(snap, factoring.descriptions(), declared, rows, factoring.provenance()))
    ts = factoring.schema_ts().relative_to(REPO)
    cache = factoring.CACHE_DIR.relative_to(REPO)
    print(f'mcp: {ts}: {sum(len(b) for b in declared.values())} extends rows over '
          f'{len(declared)} definitions, {len(rows)} alias rows ({sum(1 for r in rows if r[1] == "")} copies, '
          f'{sum(1 for r in rows if r[1])} use sites) - '
          f'{"faced under " + str(cache) if _tables_current(declared, rows) else "NOT faced under " + str(cache) + " (corpus-yoga mcp sync writes it)"}')
    for name, base in factoring.overrides(shapes, declared):
        print(f'  override: {name} extends {base} in {ts} but narrows a property of it - stands flat, since allOf cannot narrow')
    if not target.exists():
        print(f'mcp: {rel} absent - corpus-yoga mcp sync derives it')
        return 1
    have = target.read_text()
    bad = factoring.disagreements(json.loads(have), snap)
    current = have == wanted
    print(f'mcp: {rel} {"current" if current else "STALE"} with {snapshot_path.relative_to(REPO)} and {ts}'
          f' · {len(json.loads(have).get("definitions", {}))} definitions · '
          f'{"agrees with the snapshot" if not bad else f"{len(bad)} disagreement(s)"}')
    for line in bad[:5]:
        print(f'  {line}')
    if not current:
        print('  corpus-yoga mcp sync brings it current')
    return 0 if current and not bad else 1


def sync() -> int:
    target = _target()
    snapshot_path, snap = factoring.snapshot()
    shapes, declared, rows = factoring.inputs()
    if not _tables_current(declared, rows):
        for path in factoring.written_tables(declared, rows):
            print(f'  ✓ {path.relative_to(REPO)}')
    wanted = factoring.rendered(factoring.factored(snap, factoring.descriptions(), declared, rows, factoring.provenance()))
    if target.exists() and target.read_text() == wanted:
        return 0                      # current means no write and nothing said (L1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(wanted)
    print(f'  ✓ {target.relative_to(REPO)} ({len(json.loads(wanted)["definitions"])} definitions)')
    return 0


def main():
    parser = command_parser('mcp')  # generated from the declaration (#476)
    args = parser.parse_args()
    if args.verb == 'sync':
        sys.exit(sync())
    if args.verb == 'reproduce':
        script = str(REPO / 'src/main/mcp/reproduce.sh')
        os.execv(script, [script])
    sys.exit(status())


if __name__ == '__main__':
    main()
