#!/usr/bin/env python
"""
store.py (corpus-yoga store) - shared storage, data/input, as the stage has its noun (#738).

    corpus-yoga store                   # status: the units held, the duplicates, the surplus, the stage against the store
    corpus-yoga store clean             # remove what the status names: each duplicate with what only it feeds, each orphaned shadow, each surplus file

The store read in the stage's terms (src/main/corpus.py): a unit is what a pipeline's
declaration selects, at an address. Three readings, and nothing written:

  held        the units by pipeline, provider and kind, and any file no pipeline selects
              and no capturing noun writes;
  duplicates  every unit whose content another unit of its kind holds - identical, the
              same at two addresses, or contained, whole within the other's by the measure
              its pipeline declares - with the unit that holds it;
  surplus     every file inside a held unit that its measure does not read, which no
              capture wrote - a room's own sync puts one there (#833);
  staged      the stage against the store (#842): each staged unit as it stands to the held
              one of its address - promotable, held already, would lose by its relation,
              unlicensed at a version origin/main does not hold - by selection;
  live        the live stores this room mounts against the fuller of the staged and the
              held copy of each live thing (#851): each session and memory a harness holds
              beyond both, with the capture that stages it; a mount that is absent, with
              what mounts it.

The store's status reads everything upstream of it (#851): the stage against the store,
and the live stores against the fuller of the staged and the held copy
(src/main/live.py), so that it alone
names every act the room can take under next: - the captures, the rehearsal, the
promotes, the stage's cleaner and its own, in the workflow's order. The stage's status is
a report of its tier and names none.

The janitor, store clean, acts on the second reading (#744): each duplicate, of either
species, goes with what only it feeds - its members, its record and its shadow under the
cache - and the holder stays; an orphaned shadow, the cache's derivation of a unit the
store no longer holds, goes too. Its lines keep their tenses - will remove before each
act, did or did NOT after - then next:, what the room can do after the act, corpus-yoga
status last (#801), and the verdict is the last line, DONE only when every entry went.
"""
import sys
from pathlib import Path

SELF = 'src/main/cli/store/store.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main'))
from declared_parser import command_parser  # noqa: E402
import cleaner  # noqa: E402 - the one loop every clean verb runs (#837)
import corpus  # noqa: E402
import facts  # noqa: E402
import live  # noqa: E402 - the live stores: their addresses, which the duplicates reading keeps the newest of (#744), and their reading against both tiers (#851)


KINDS = {'duplicate': 'duplicates', 'orphaned shadow': 'orphaned shadows', 'surplus file': 'surplus files'}   # each kind of entry, and its plural


def _dispose_all(paths: list[Path]) -> str | None:
    for path in paths:
        why = corpus.dispose(path)
        if why is not None:
            return f'{path.relative_to(REPO) if path.is_relative_to(REPO) else path}: {why}'
    return None


def entries() -> list[cleaner.Entry]:
    """Everything the janitor acts on, in the order it acts, each with its kind, its address
    or path, its facts, the act, and the selection it is counted under. The one list both
    faces walk."""
    out: list[cleaner.Entry] = []
    for duplicate in corpus.held_twice(corpus.STORE, *live.live_addresses()):
        unit, holder, how, by = duplicate.unit, duplicate.holder, duplicate.how, duplicate.by
        paths = [corpus.STORE / m for m in unit.members + unit.record]
        own = corpus.shadow(unit)
        if own is not None and own.exists():
            paths.append(own)
        out.append(cleaner.Entry('duplicate', unit.address.as_posix(),
                                 {'duplicate': facts.sentence('identical to {holder}' if how == 'identical' else 'contained by {holder}', holder=holder.address.as_posix()), 'by': by,
                                  'size': corpus.human(sum(corpus.size_of(p) for p in paths)),
                                  'goes': [p.relative_to(REPO).as_posix() if p.is_relative_to(REPO) else str(p) for p in paths]},
                                 lambda paths=paths: _dispose_all(paths), corpus.kind_of(unit)))
    for d in corpus.orphaned_shadows():
        shadow = d.relative_to(REPO).as_posix()
        out.append(cleaner.Entry('orphaned shadow', shadow,
                                 {'orphaned shadow': facts.sentence('the store holds no unit it derives from'), 'size': corpus.human(corpus.size_of(d))},
                                 lambda d=d: _dispose_all([d]), '/'.join(shadow.split('/')[:3])))
    for unit, rel in corpus.surplus(corpus.STORE):
        out.append(cleaner.Entry('surplus file', rel.as_posix(),
                                 {'surplus file': facts.sentence('its measure does not read it, and no capture wrote it'), 'beside': f'{unit.path.name}.json',
                                  'size': corpus.human(corpus.size_of(corpus.STORE / rel))},
                                 lambda rel=rel: _dispose_all([corpus.STORE / rel]), corpus.kind_of(unit)))
    return out


def store_next(rows: list[corpus.Judged], ahead: list[live.Ahead]) -> dict[str, dict[str, dict[str, int]]]:
    """What to run next, by command, in the workflow's order (#851): the room's one reading,
    corpus.room_next, over the rows and the live reading this status has already read."""
    return corpus.room_next(rows, ahead)


def status_facts() -> corpus.StoreStatus:
    """Bare corpus-yoga store, whole: the store's own readings, the stage against the
    store, the live stores against both tiers, and what to run next."""
    out, held, twice = corpus.store_facts(*live.live_addresses())
    rows = corpus.survey()
    out.staged = corpus.promotion_facts(rows) if rows else facts.sentence('none staged')
    out.would_lose = corpus.relation_would_lose(rows) or None
    ahead, absent = live.ahead()
    items, found, level = live.ahead_facts(ahead, absent)
    out.live = items if items else (facts.sentence('no live store is mounted in this workspace') if not ahead
                                    else facts.sentence('nothing beyond the tiers - {level} live unit(s) level with the copies', level=level))
    out.next = store_next(rows, ahead) or facts.sentence('none - nothing to do')
    return out


def clean() -> int:
    return cleaner.clean('store', entries(), KINDS, corpus.room_next)


def main() -> int:
    args = command_parser('store').parse_args()
    if args.verb == 'clean':
        return clean()
    facts.say(status_facts())
    return 0


if __name__ == '__main__':
    sys.exit(main())
