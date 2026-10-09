#!/usr/bin/env python
"""
store.py (corpus-yoga store) - shared storage, data/input, as the stage has its noun (#738).

    corpus-yoga store                   # status: the units held, the duplicates, the surplus, the stage against the store
    corpus-yoga store clean --dry-run   # what the janitor would remove: each duplicate with what only it feeds, each orphaned shadow
    corpus-yoga store clean --apply     # remove it

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
              one of its address - promotable, held already, refused by its relation - by
              selection, with the promote, the stage's cleaner and this janitor as the next
              steps.

A tier's status compares the tier with the tier that feeds it: the stage feeds the store,
so the store reads the stage; the live stores feed the stage, so the stage reads them
(src/main/live.py), and this noun reads no live store.

The janitor, store clean, acts on the second reading (#744): each duplicate, of either
species, goes with what only it feeds - its members, its record and its shadow under the
cache - and the holder stays; an orphaned shadow, the cache's derivation of a unit the
store no longer holds, goes too. Its lines keep their tenses - will remove before each
act, did or did NOT after - the status is re-read beneath them, and the verdict is the
last line, DONE only when every entry went; the dry run is the apply with the act elided.
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
import live  # noqa: E402 - the live stores' addresses, which the duplicates reading keeps the newest of (#744)


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
                                 {'duplicate': f'{"identical to" if how == "identical" else "contained by"} {holder.address.as_posix()}', 'by': by,
                                  'size': corpus.human(sum(corpus.size_of(p) for p in paths)),
                                  'goes': [p.relative_to(REPO).as_posix() if p.is_relative_to(REPO) else str(p) for p in paths]},
                                 lambda paths=paths: _dispose_all(paths), corpus.kind_of(unit)))
    for d in corpus.orphaned_shadows():
        shadow = d.relative_to(REPO).as_posix()
        out.append(cleaner.Entry('orphaned shadow', shadow,
                                 {'orphaned shadow': 'the store holds no unit it derives from', 'size': corpus.human(corpus.size_of(d))},
                                 lambda d=d: _dispose_all([d]), '/'.join(shadow.split('/')[:3])))
    for unit, rel in corpus.surplus(corpus.STORE):
        out.append(cleaner.Entry('surplus file', rel.as_posix(),
                                 {'surplus file': 'its measure does not read it, and no capture wrote it', 'beside': f'{unit.path.name}.json',
                                  'size': corpus.human(corpus.size_of(corpus.STORE / rel))},
                                 lambda rel=rel: _dispose_all([corpus.STORE / rel]), corpus.kind_of(unit)))
    return out


def store_next() -> dict[str, dict[str, dict[str, int]]]:
    """What to run next, by command: its verb, then each kind it acts on with how many -
    each capturing noun's promote for what the stage holds promotable, the stage's cleaner
    for what the stage holds that the store already does, and this janitor for what the
    store no longer needs, by the selection each entry is counted under."""
    out = corpus.promotion_next(corpus.survey())
    for entry in entries():
        corpus.step(out, 'corpus-yoga store clean --apply', entry.under)
    return out


def status_facts() -> corpus.StoreStatus:
    """Bare corpus-yoga store, whole: the store's own readings, the stage against the
    store, and what to run next."""
    out, held, twice = corpus.store_facts(*live.live_addresses())
    rows = corpus.survey()
    out.staged = corpus.promotion_facts(rows) if rows else 'none staged'
    out.refused = corpus.relation_refused(rows) or None
    out.next = store_next() or 'none - nothing to do'
    return out


def clean(apply: bool) -> int:
    return cleaner.clean('store', entries(), KINDS, lambda: facts.say(status_facts()), apply)


def main() -> int:
    args = command_parser('store').parse_args()
    if args.verb == 'clean':
        return clean(bool(args.apply))
    facts.say(status_facts())
    return 0


if __name__ == '__main__':
    sys.exit(main())
