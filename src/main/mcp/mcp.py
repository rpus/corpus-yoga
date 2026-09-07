#!/usr/bin/env python
"""
mcp.py - the house factoring of the MCP schema, rsc/schema/protocol/mcpMessage,
derived from its verbatim snapshot rsc/reference/mcp.

`mcp` is a NOUN: the derived schema. A bare invocation shows their state and
writes nothing (the bare noun IS the status). Only `sync` writes: it brings the
family's latest version file into agreement with the snapshot, and re-running is
silence (L1). The witness that the derivation preserved meaning is the dev gate's
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


def status() -> int:
    target = _target()
    rel = target.relative_to(REPO)
    wanted = factoring.current_text()
    if not target.exists():
        print(f'mcp: {rel} absent - corpus-yoga mcp sync derives it')
        return 1
    have = target.read_text()
    snapshot_path, snap = factoring.snapshot()
    bad = factoring.disagreements(json.loads(have), snap)
    current = have == wanted
    print(f'mcp: {rel} {"current" if current else "STALE"} with {snapshot_path.relative_to(REPO)}'
          f' · {len(json.loads(have).get("definitions", {}))} definitions · '
          f'{"agrees with the snapshot" if not bad else f"{len(bad)} disagreement(s)"}')
    for line in bad[:5]:
        print(f'  {line}')
    for name, base in factoring.overrides(*factoring.shapes_and_declared()):
        print(f'  override: {name} narrows {base} - stands flat (schema.ts extends, allOf cannot)')
    if not current:
        print('  corpus-yoga mcp sync brings it current')
    return 0 if current and not bad else 1


def sync() -> int:
    target = _target()
    wanted = factoring.current_text()
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
