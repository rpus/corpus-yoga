#!/usr/bin/env python
"""
input.py (corpus-yoga input) - what this room has captured and not yet promoted.

A capture writes under tmp/input, at the address its unit will have under data/input,
and reads nothing (L10). This command is the one reduce over the room's input against the store
(#687): bare, each staged unit and where it stands to the held one of its address;
`promote`, the units the relation licenses written into shared storage and taken off
tmp/input, the rest named and left - a dry run unless --apply.

    corpus-yoga input                                      # status: each staged unit's relation
    corpus-yoga input promote --all                        # what would be promoted, and what refused
    corpus-yoga input promote --provider <p> [--id <unit>] # one provider's units, or one of them
    corpus-yoga input promote ... --apply                  # promote

The extent is named as the agent capture names it: --all, or --provider, or
--provider with --id, where --id is a prefix of the unit's address under the
provider matching exactly one; a uuid's shape does not say whose it is.

The relations are src/main/append_only.py's; the measure each kind is related by is
src/main/input.py's. A unit is promoted on ABSENT (new) and EXTENDS (the held unit
gains and loses nothing); an IDENTICAL unit is taken out of tmp/input unwritten; an AHEAD
unit (the staged copy holds less than the held one - a short walk, a truncated fetch)
and a DIVERGED one (each side holds what the other lacks) are refused, named with
what the reader can do, and left staged.
"""
import shutil
import sys
from pathlib import Path

SELF = 'src/main/cli/input/input.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main'))
from declared_parser import command_parser  # noqa: E402
from append_only import Relation, may_replace  # noqa: E402
import input as staging  # noqa: E402

REMEDY = {
    Relation.AHEAD:    'the held unit holds more - recapture, or remove the staged copy: rm -r tmp/input/{unit}',
    Relation.DIVERGED: 'each holds what the other lacks - inspect both, then keep one: rm -r tmp/input/{unit} keeps the held',
}


def survey() -> list[tuple[Path, Relation, str]]:
    if not staging.STAGE.is_dir():
        return []
    return [(u, *staging.relation(u)) for u in staging.units(staging.STAGE)]


def word(unit: Path, relation: Relation, detail: str) -> str:
    verb = {Relation.ABSENT: 'new', Relation.IDENTICAL: 'identical', Relation.EXTENDS: 'extends',
            Relation.AHEAD: 'AHEAD - refused', Relation.DIVERGED: 'DIVERGED - refused'}[relation]
    return f'  {unit}: {verb} ({detail})'


def status() -> int:
    rows = survey()
    if not rows:
        print('tmp/input: nothing staged - every capture this room has made is promoted')
        return 0
    counts = {r: 0 for r in Relation}
    for unit, relation, detail in rows:
        counts[relation] += 1
        print(word(unit, relation, detail))
    promotable = counts[Relation.ABSENT] + counts[Relation.EXTENDS]
    refused = counts[Relation.AHEAD] + counts[Relation.DIVERGED]
    print(f'tmp/input: {len(rows)} unit(s) - {promotable} promotable, {counts[Relation.IDENTICAL]} identical, '
          f'{refused} refused' + (' - corpus-yoga input promote --apply promotes' if promotable or counts[Relation.IDENTICAL] else ''))
    return 0


def extent(rows, provider: str | None, unit_id: str | None) -> list:
    """The units the flags name, or a refusal that names what they matched."""
    if provider is None:
        return rows
    mine = [r for r in rows if r[0].parts[0] == provider]
    if unit_id is None:
        return mine
    hits = [r for r in mine if any(part.startswith(unit_id) for part in r[0].parts[1:]) or
            r[0].relative_to(provider).as_posix().startswith(unit_id)]
    if len(hits) != 1:
        names = ', '.join(str(r[0]) for r in hits) or 'nothing'
        sys.exit(f'error: --id {unit_id!r} names {len(hits)} staged unit(s) of {provider}: {names} - '
                 f'--id names one; corpus-yoga input lists them')
    return hits


def promote(apply: bool, provider: str | None, unit_id: str | None) -> int:
    rows = extent(survey(), provider, unit_id)
    if not rows:
        print('input promote: nothing staged' + (f' for {provider}' if provider else ''))
        return 0
    written = cleared = refused = 0
    for unit, relation, detail in rows:
        s, h = staging.STAGE / unit, staging.STORE / unit
        if may_replace(relation):
            print(word(unit, relation, detail) + (' - promoted' if apply else ' - would promote'))
            if apply:
                h.parent.mkdir(parents=True, exist_ok=True)
                if h.exists():
                    shutil.rmtree(h) if h.is_dir() else h.unlink()
                shutil.move(str(s), str(h))
            written += 1
        elif relation is Relation.IDENTICAL:
            print(word(unit, relation, detail) + (' - cleared from tmp/input' if apply else ' - would clear from tmp/input'))
            if apply:
                shutil.rmtree(s) if s.is_dir() else s.unlink()
            cleared += 1
        else:
            print(word(unit, relation, detail))
            print('    ' + REMEDY[relation].format(unit=unit))
            refused += 1
    if apply:
        _prune_empty(staging.STAGE)
    done = 'DONE' if apply else 'would'
    print(f'input promote: {done} - {written} promoted, {cleared} identical cleared, {refused} refused and left staged'
          + ('' if apply else ' (--apply performs it)'))
    return 1 if refused else 0


def _prune_empty(root: Path) -> None:
    for d in sorted((p for p in root.rglob('*') if p.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()


def main() -> int:
    args = command_parser('input').parse_args()
    if args.verb == 'promote':
        if args.id is not None and args.provider is None:
            sys.exit('error: --id names a unit within a provider - say which with --provider')
        return promote(args.apply, args.provider, args.id)
    return status()


if __name__ == '__main__':
    sys.exit(main())
