#!/usr/bin/env python
"""
input.py (corpus-yoga input) - what this room has captured and not yet promoted.

A capture writes under tmp/input, at the address its unit will have under data/input,
and reads nothing (L10). This bare noun is the report over the room's input: each
staged unit, where it stands to the held one of its address, whether the pipelines
have found it valid, and which noun's promote verb reaches it. It writes nothing.

    corpus-yoga input        # each staged unit's relation and verdict

What a unit is, the measure each kind is related by, the verdict - the pipelines'
cached logs at origin/main's versions, made by corpus-yoga pipeline run --overlay - and
the promote verbs themselves (corpus-yoga browser|agent|export|forge promote) are
src/main/input.py's. A unit is promoted on ABSENT (new) and EXTENDS (the held unit gains
and loses nothing) with a green verdict, or with none where no family validates its
kind; an IDENTICAL unit is taken out of tmp/input unwritten; an AHEAD unit (the staged
copy holds less than the held one - a short walk, a truncated fetch), a DIVERGED one
(each side holds what the other lacks), and one with no verdict or a red one are
refused, named with what the reader can do, and left staged.
"""
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
from append_only import Relation  # noqa: E402
import input as staging  # noqa: E402


def status() -> int:
    rows = staging.survey()
    if not rows:
        print('tmp/input: nothing staged - every capture this room has made is promoted')
        return 0
    n_identical = n_refused = 0
    by_noun: dict[str, int] = {}
    for unit, rel, detail, ok, words in rows:
        print(staging.word(unit, rel, detail, ok, words))
        if rel is Relation.IDENTICAL:
            n_identical += 1
        elif staging.promotable(rel, ok):
            by_noun[staging.noun_of(unit) or '?'] = by_noun.get(staging.noun_of(unit) or '?', 0) + 1
        else:
            n_refused += 1
    n_promote = sum(by_noun.values())
    print(f'tmp/input: {len(rows)} unit(s) - {n_promote} promotable, {n_identical} identical, {n_refused} refused'
          + ''.join(f'; corpus-yoga {noun} promote --all promotes {n}' for noun, n in sorted(by_noun.items())))
    return 0


def main() -> int:
    command_parser('input').parse_args()
    return status()


if __name__ == '__main__':
    sys.exit(main())
