#!/usr/bin/env python
"""
mcp.py - the house factoring of the MCP schema, rsc/schema/protocol/mcpMessage,
generated from upstream's schema.ts alone (#598): read through the parser generated
from the house TypeScript grammar (#597) by mcp_generation.py into the flat shape of
every declaration, composed over the extends clauses and tagged by the categories
mcp_extraction.py reads (#581, #595); upstream's schema.json beside it is the witness
every definition must flatten to, never a source.

`mcp` is a NOUN: the derived schema. A bare invocation shows its state and writes
nothing (the bare noun IS the status). Only `sync` writes: the two extracted
tables under tmp/cache/mcp/ (the readable face of the derivation's inputs) and the
family's version file - and it MINTS (#583): when the derivation differs from the
latest version file in any way, it prints the diff, writes the next version and
removes the current one, by plain file operations (git sees a rename by
similarity, as it would after git mv). A version of this family means one thing:
the derivation's output changed. The changelog section stays a hand act, owed at
the commit gate by schema.changelog_narrative. Re-running is silence (L1). The witness that the derivation preserved meaning is the dev gate's
(mcp.factoring_agrees); the currency of the committed file is its too
(mcp.factoring_current).

Usage:
    corpus-yoga mcp              # status: is rsc/schema/protocol/mcpMessage current with the snapshot?
    corpus-yoga mcp sync         # (re-)derive rsc/schema/protocol/mcpMessage/v*.json: the diff, then the
                                 # next version minted when anything differs - idempotent
    corpus-yoga mcp reproduce    # is the snapshot's schema.json what upstream's generator makes of its
                                 # schema.ts? - src/main/mcp/reproduce.sh, whose header states the run
"""

import difflib
import json
import os
import re
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


def _successor(version: Path) -> Path:
    n = int(re.findall(r'\d+', version.stem)[-1])
    return version.with_name(f'v{n + 1}.json')


def _diff(have: str, wanted: str, have_name: str, wanted_name: str) -> str:
    return ''.join(difflib.unified_diff(have.splitlines(keepends=True), wanted.splitlines(keepends=True),
                                        fromfile=have_name, tofile=wanted_name))


def _tables_current(declared: dict) -> bool:
    """Whether tmp/cache/mcp/ holds the tables as extracted now."""
    import tempfile
    with tempfile.TemporaryDirectory() as scratch:
        saved = factoring.CACHE_DIR, factoring.COMPOSITION, factoring.CATEGORIES
        try:
            factoring.CACHE_DIR = Path(scratch)
            factoring.COMPOSITION = factoring.CACHE_DIR / 'composition.csv'
            factoring.CATEGORIES = factoring.CACHE_DIR / 'category.csv'
            fresh = {p.name: p.read_text() for p in factoring.written_tables(declared, factoring.categories())}
        finally:
            factoring.CACHE_DIR, factoring.COMPOSITION, factoring.CATEGORIES = saved
    return all((factoring.CACHE_DIR / name).is_file() and (factoring.CACHE_DIR / name).read_text() == text
               for name, text in fresh.items())


def status() -> int:
    target = _target()
    rel = target.relative_to(REPO)
    snapshot_path, snap = factoring.snapshot()
    try:
        shapes, declared = factoring.inputs()
    except AssertionError as e:                 # the parser absent, or schema.ts refused
        print(f'mcp: {target.relative_to(REPO)} NOT derivable - {e}')
        return 1
    try:
        wanted = factoring.rendered(factoring.factored(shapes, factoring.descriptions(), declared, factoring.provenance(), factoring.unreachable(),
                                                       factoring.categories(), factoring.layer_rule(), factoring.placements(factoring.provenance()['lineage']),
                                                       factoring.additions(), factoring.generated().constants))
    except AssertionError as e:
        print(f'mcp: {target.relative_to(REPO)} NOT derivable - {e}')
        return 1
    ts = factoring.schema_ts().relative_to(REPO)
    cache = factoring.CACHE_DIR.relative_to(REPO)
    tagged = factoring.categories()
    gen = factoring.generated()
    print(f'mcp: {ts}: {len(gen.interfaces)} interfaces, {len(gen.aliases)} aliases and {len(gen.constants)} constants generated; '
          f'{sum(len(b) for b in declared.values())} extends rows over {len(declared)} definitions, '
          f'{sum(1 for t in tagged.values() if t)} category tags over {len(tagged)} declarations - '
          f'{"faced under " + str(cache) if _tables_current(declared) else "NOT faced under " + str(cache) + " (corpus-yoga mcp sync writes it)"}')
    for row in factoring.additions():
        print(f'  addition: {row["definition"]} at {row["pointer"]} reads {row["house"] or "nothing"} here, {row["upstream"] or "nothing"} upstream - rsc/schema/protocol/mcpMessage/addition.csv')
    for name, base in factoring.overrides(shapes, declared):
        print(f'  override: {name} extends {base} in {ts} but narrows a property of it - stands flat, since allOf cannot narrow')
    for union, request in factoring.uncarried_results(shapes):
        print(f'  uncarried: {union} - no message carries it, since {ts} declares no {request} - stands unreachable, '
              f'declared in {factoring.UNREACHABLE.relative_to(REPO)}')
    if not target.exists():
        print(f'mcp: {rel} absent - corpus-yoga mcp sync derives it')
        return 1
    have = target.read_text()
    bad = factoring.disagreements(json.loads(have), snap, factoring.additions(), factoring.generated().constants)
    current = have == wanted
    print(f'mcp: {rel} {"current" if current else "STALE"} with {snapshot_path.relative_to(REPO)} and {ts}'
          f' · {len(json.loads(have).get("definitions", {}))} definitions · '
          f'{"agrees with the snapshot" if not bad else f"{len(bad)} disagreement(s)"}')
    print('  layers: ' + ' · '.join(f'{layer} {n}' for layer, n in factoring.partition(json.loads(wanted)).items()))
    for line in bad[:5]:
        print(f'  {line}')
    if not current:
        changed = sum(1 for l in _diff(have, wanted, rel.name, 'derivation').splitlines()
                      if l[:1] in '+-' and not l.startswith(('+++', '---')))
        print(f'  the derivation differs by {changed} line(s) - corpus-yoga mcp sync prints the diff and '
              f'mints {_successor(target).name} in place of {rel.name}')
    return 0 if current and not bad else 1


def sync() -> int:
    target = _target()
    snapshot_path, snap = factoring.snapshot()
    try:
        shapes, declared = factoring.inputs()
    except AssertionError as e:                 # the parser absent, or schema.ts refused
        print(f'mcp: {target.relative_to(REPO)} NOT derivable - {e}')
        return 1
    if not _tables_current(declared):
        for path in factoring.written_tables(declared, factoring.categories()):
            print(f'  ✓ {path.relative_to(REPO)}')
    try:
        wanted = factoring.rendered(factoring.factored(shapes, factoring.descriptions(), declared, factoring.provenance(), factoring.unreachable(),
                                                       factoring.categories(), factoring.layer_rule(), factoring.placements(factoring.provenance()['lineage']),
                                                       factoring.additions(), factoring.generated().constants))
    except AssertionError as e:
        print(f'mcp: {target.relative_to(REPO)} NOT derivable - {e}')
        return 1
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(wanted)
        print(f'  ✓ {target.relative_to(REPO)} ({len(json.loads(wanted)["definitions"])} definitions)')
        return 0
    have = target.read_text()
    if have == wanted:
        return 0                      # current means no write and nothing said (L1)
    # The mint (#583): the diff, then the next version in place of this one. Two
    # file operations, no git - the commit is the user's act, and git reads the
    # rename by similarity as it would after git mv.
    minted = _successor(target)
    rel, minted_rel = target.relative_to(REPO), minted.relative_to(REPO)
    sys.stdout.write(_diff(have, wanted, str(rel), str(minted_rel)))
    minted.write_text(wanted)
    target.unlink()
    print(f'  ✓ {minted_rel} minted in place of {rel} ({len(json.loads(wanted)["definitions"])} definitions) - '
          f'write its ## {minted.stem} section in {factoring.FAMILY_DIR.relative_to(REPO)}/CHANGELOG.md '
          f'(the commit gate holds schema.changelog_narrative)')
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
