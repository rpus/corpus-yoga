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

The relations are src/main/append_only.py's; the measure each kind is related by, and
the verdict - the pipelines' cached logs at origin/main's versions, made by
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
from append_only import Relation, may_replace, relate  # noqa: E402
import input as staging  # noqa: E402

REMEDY = {
    Relation.AHEAD:    'the held unit holds more - recapture, or remove the staged copy: rm -r tmp/input/{unit}',
    Relation.DIVERGED: 'each holds what the other lacks - inspect both, then keep one: rm -r tmp/input/{unit} keeps the held',
}


def survey() -> list[tuple[Path, list[Path], Relation, str, bool | None, str]]:
    """(unit, its files, relation, the relation's words, verdict, the verdict's words)."""
    if not staging.STAGE.is_dir():
        return []
    rows = []
    for unit, files in staging.units(staging.STAGE).items():
        relation, detail = staging.relation(unit)
        ok, words = staging.verdict(unit) if may_replace(relation) else (None, '')
        rows.append((unit, files, relation, detail, ok, words))
    return rows


def promotable(relation: Relation, ok: bool | None) -> bool:
    return may_replace(relation) and ok is not False


def word(unit: Path, relation: Relation, detail: str, ok: bool | None, words: str) -> str:
    verb = {Relation.ABSENT: 'new', Relation.IDENTICAL: 'identical', Relation.EXTENDS: 'extends',
            Relation.AHEAD: 'AHEAD - refused', Relation.DIVERGED: 'DIVERGED - refused'}[relation]
    line = f'  {unit}: {verb} ({detail})'
    if may_replace(relation):
        line += f'; {words}' if ok is not False else f'; REFUSED - {words}'
    return line


def status() -> int:
    rows = survey()
    if not rows:
        print('tmp/input: nothing staged - every capture this room has made is promoted')
        return 0
    n_promote = n_identical = n_refused = 0
    for unit, _files, relation, detail, ok, words in rows:
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
    mine = [r for r in rows if r[0].parts[0] == provider]
    if unit_id is None:
        return mine
    hits = [r for r in mine if any(part.startswith(unit_id) for part in r[0].parts[1:])]
    if len(hits) != 1:
        names = ', '.join(str(r[0]) for r in hits) or 'nothing'
        sys.exit(f'error: --id {unit_id!r} names {len(hits)} staged unit(s) of {provider}: {names} - '
                 f'--id names one; corpus-yoga input lists them')
    return hits


def _place(unit: Path, files: list[Path]) -> None:
    """Write the unit into the store: a directory unit replaces the held directory whole; a
    claude session's log replaces the held log and its workspace files each move by prefix,
    a file the held workspace is ahead of or diverged from left staged."""
    s, h = staging.STAGE / unit, staging.STORE / unit
    if s.is_dir() or s.is_file():
        h.parent.mkdir(parents=True, exist_ok=True)
        if h.exists() or h.is_symlink():
            shutil.rmtree(h) if h.is_dir() else h.unlink()
        shutil.move(str(s), str(h))
        return
    for rel in files:                                    # a claude session: log and workspace files
        src, dst = staging.STAGE / rel, staging.STORE / rel
        r = relate(src.read_bytes(), dst.read_bytes() if dst.exists() else None)
        if may_replace(r) or r is Relation.IDENTICAL:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if r is Relation.IDENTICAL:
                src.unlink()
            else:
                shutil.move(str(src), str(dst))
        else:
            print(f'    {rel}: {r.value} - left staged')


def _clear(unit: Path, files: list[Path]) -> None:
    s = staging.STAGE / unit
    if s.is_dir():
        shutil.rmtree(s)
    elif s.is_file():
        s.unlink()
    else:
        for rel in files:
            (staging.STAGE / rel).unlink()


def promote(apply: bool, provider: str | None, unit_id: str | None) -> int:
    rows = extent(survey(), provider, unit_id)
    if not rows:
        print('input promote: nothing staged' + (f' for {provider}' if provider else ''))
        return 0
    written = cleared = refused = 0
    for unit, files, relation, detail, ok, words in rows:
        if relation is Relation.IDENTICAL:
            print(word(unit, relation, detail, ok, words) + (' - cleared from tmp/input' if apply else ' - would clear from tmp/input'))
            if apply:
                _clear(unit, files)
            cleared += 1
        elif promotable(relation, ok):
            print(word(unit, relation, detail, ok, words) + (' - promoted' if apply else ' - would promote'))
            if apply:
                _place(unit, files)
            written += 1
        else:
            print(word(unit, relation, detail, ok, words))
            if relation in REMEDY:
                print('    ' + REMEDY[relation].format(unit=unit))
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
