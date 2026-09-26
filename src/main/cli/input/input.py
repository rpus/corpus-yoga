#!/usr/bin/env python
"""
input.py (corpus-yoga input) - what this room has captured and not yet promoted.

A capture writes under tmp/input, at the address its unit will have under data/input,
and reads nothing (L10). This command is the one reduce over the room's input against
the store (#687): bare, each staged unit, where it stands to the held one of its address,
and whether the pipelines have found it valid; `promote`, the units the relation and the
verdict together license, written into shared storage and taken out of tmp/input, the
rest named and left - a dry run unless --apply.

    corpus-yoga input                                      # status: each unit's relation and verdict
    corpus-yoga input promote --all                        # what would be promoted, and what refused
    corpus-yoga input promote --provider <p> [--id <unit>] # one provider's units, or one of them
    corpus-yoga input promote ... --apply                  # promote

What a unit is (the pipeline declarations' selection), the measure each kind is related
by, and the verdict - the pipelines' cached logs at origin/main's versions, made by
corpus-yoga pipeline run --overlay - are src/main/input.py's. A unit is promoted on
ABSENT (new) and EXTENDS (the held unit gains and loses nothing) with a green verdict,
or with none where no pipeline validates its kind; an IDENTICAL unit is taken out of
tmp/input unwritten; an AHEAD unit (the staged copy holds less than the held one - a
short walk, a truncated fetch), a DIVERGED one (each side holds what the other lacks),
and one with no verdict or a red one are refused, named with what the reader can do,
and left staged.

The extent is named as the agent capture names it: --all, or --provider, or
--provider with --id, where --id is a prefix of the unit's address under the
provider matching exactly one; a uuid's shape does not say whose it is.
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
from input import Unit  # noqa: E402

REMEDY = {
    Relation.AHEAD:    'the held unit holds more - recapture, or remove the staged copy: rm -r tmp/input/{unit}',
    Relation.DIVERGED: 'each holds what the other lacks - inspect both, then keep one: rm -r tmp/input/{unit} keeps the held',
}


def survey() -> list[tuple[Unit, Relation, str, bool | None, str]]:
    """(unit, relation, the relation's words, verdict, the verdict's words)."""
    rows = []
    for unit in staging.units(staging.STAGE):
        relation, detail = staging.relation(unit)
        ok, words = staging.verdict(unit) if may_replace(relation) else (None, '')
        rows.append((unit, relation, detail, ok, words))
    return rows


def promotable(relation: Relation, ok: bool | None) -> bool:
    return may_replace(relation) and ok is not False


def word(unit: Unit, relation: Relation, detail: str, ok: bool | None, words: str) -> str:
    verb = {Relation.ABSENT: 'new', Relation.IDENTICAL: 'identical', Relation.EXTENDS: 'extends',
            Relation.AHEAD: 'AHEAD - refused', Relation.DIVERGED: 'DIVERGED - refused'}[relation]
    line = f'  {unit.address}: {verb} ({detail})'
    if may_replace(relation):
        line += f'; {words}' if ok is not False else f'; REFUSED - {words}'
    return line


def status() -> int:
    rows = survey()
    if not rows:
        print('tmp/input: nothing staged - every capture this room has made is promoted')
        return 0
    n_promote = n_identical = n_refused = 0
    for unit, relation, detail, ok, words in rows:
        print(word(unit, relation, detail, ok, words))
        if relation is Relation.IDENTICAL:
            n_identical += 1
        elif promotable(relation, ok):
            n_promote += 1
        else:
            n_refused += 1
    print(f'tmp/input: {len(rows)} unit(s) - {n_promote} promotable, {n_identical} identical, {n_refused} refused'
          + (' - corpus-yoga input promote --all --apply promotes' if n_promote or n_identical else ''))
    return 0


def extent(rows, provider: str | None, unit_id: str | None) -> list:
    """The units the flags name, or a refusal that names what they matched."""
    if provider is None:
        return rows
    mine = [r for r in rows if r[0].address.parts[0] == provider]
    if unit_id is None:
        return mine
    hits = [r for r in mine if any(part.startswith(unit_id) for part in r[0].address.parts[1:])]
    if len(hits) != 1:
        names = ', '.join(str(r[0].address) for r in hits) or 'nothing'
        sys.exit(f'error: --id {unit_id!r} names {len(hits)} staged unit(s) of {provider}: {names} - '
                 f'--id names one; corpus-yoga input lists them')
    return hits


def _place(unit: Unit) -> None:
    """Write the unit into the store: each of its members - its directory, or its file and
    the companion that moves with it - replaces the held one whole."""
    for rel in unit.members:
        s, h = staging.STAGE / rel, staging.STORE / rel
        h.parent.mkdir(parents=True, exist_ok=True)
        if h.is_symlink() or h.is_file():
            h.unlink()
        elif h.is_dir():
            shutil.rmtree(h)
        shutil.move(str(s), str(h))


def _clear(unit: Unit) -> None:
    for rel in unit.members:
        s = staging.STAGE / rel
        if s.is_dir():
            shutil.rmtree(s)
        elif s.exists():
            s.unlink()


def promote(apply: bool, provider: str | None, unit_id: str | None) -> int:
    rows = extent(survey(), provider, unit_id)
    if not rows:
        print('input promote: nothing staged' + (f' for {provider}' if provider else ''))
        return 0
    written = cleared = refused = 0
    for unit, relation, detail, ok, words in rows:
        if relation is Relation.IDENTICAL:
            print(word(unit, relation, detail, ok, words) + (' - cleared from tmp/input' if apply else ' - would clear from tmp/input'))
            if apply:
                _clear(unit)
            cleared += 1
        elif promotable(relation, ok):
            print(word(unit, relation, detail, ok, words) + (' - promoted' if apply else ' - would promote'))
            if apply:
                _place(unit)
            written += 1
        else:
            print(word(unit, relation, detail, ok, words))
            if relation in REMEDY:
                print('    ' + REMEDY[relation].format(unit=unit.address))
            refused += 1
    if apply:
        _prune_empty(staging.STAGE)
    done = 'DONE' if apply else 'would'
    print(f'input promote: {done} - {written} promoted, {cleared} identical cleared, {refused} refused and left staged'
          + ('' if apply else ' (--apply performs it)'))
    return 1 if refused else 0


def _prune_empty(root: Path) -> None:
    if not root.is_dir():
        return
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
