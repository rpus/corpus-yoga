#!/usr/bin/env python
"""
stage.py (corpus-yoga stage) - the room's stage, tmp/stage, as the cache has its noun.

    corpus-yoga stage                   # status: the input, the scratch, each orphan, the rehearsal record, the units' counts
    corpus-yoga stage clean --dry-run   # what the janitor would remove: each orphan, each duplicate of a held unit, each incomplete unit
    corpus-yoga stage clean --apply     # remove it

The tier (src/main/tier.py, src/main/corpus.py): input is what the captures write; scratch
is what the last rehearsal's run derived, replaced whole by the next; rehearsal.json is
the record, one file, what the last rehearsal saw and judged (src/main/rehearsal.py, #815).
The per-unit relations stay with each capturing noun's bare status and with bare
corpus-yoga pipeline; this face counts them against the record. The janitor clears its
tier as corpus-yoga cache clean clears its own: every staged unit identical to the held
one, a duplicate, already promoted; every unit whose record or payload is absent,
incomplete; and every entry under tmp/stage that is neither the input, the scratch nor
the record, an orphan of an earlier layout. The scratch and the record are the
rehearsal's to replace, never the janitor's; a refused unit is evidence of another kind
and is never the janitor's.

The janitor's faces are src/main/cleaner.py's, the one loop every clean verb runs (#837):
this noun names its entries - each orphan, duplicate and incomplete unit, keyed by its
address with its kind, its words and its size beneath - and the loop says and takes them.
An entry is removed as it stands at the act, not as it stood at the naming: a directory
that gained a file while being emptied is emptied again.
"""
import sys
from pathlib import Path

SELF = 'src/main/cli/stage/stage.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main'))
from declared_parser import command_parser  # noqa: E402
import cleaner  # noqa: E402 - the one loop every clean verb runs (#837)
import corpus  # noqa: E402

KINDS = {'orphan': 'orphans', 'duplicate': 'duplicates', 'incomplete unit': 'incomplete units'}   # each kind of entry, and its plural


def _unit(unit: corpus.Unit) -> str | None:
    try:
        corpus.remove(unit)
    except OSError as e:
        return (e.strerror or str(e)).lower()
    return None


def _size(unit: corpus.Unit) -> str:
    return corpus.human(sum(corpus.size_of(corpus.STAGE / m) for m in unit.members + unit.record if (corpus.STAGE / m).exists()))


def entries() -> list[cleaner.Entry]:
    """Everything the janitor acts on, in the order it acts, each with its kind, its address,
    its facts and the act. The one list both faces walk - the dry run is the apply with the
    act elided, so the two cannot disagree."""
    out: list[cleaner.Entry] = []
    for e in corpus.orphans():
        name = e.relative_to(REPO).as_posix()
        out.append(cleaner.Entry('orphan', name, {'orphan': 'neither the input, the scratch nor the record', 'size': corpus.human(corpus.size_of(e))},
                                 lambda e=e: corpus.dispose(e)))
    if corpus.STAGE.is_dir():
        for unit in corpus.units(corpus.STAGE):
            if corpus.redundant(unit):
                out.append(cleaner.Entry('duplicate', unit.address.as_posix(), {'duplicate': 'identical to the held unit', 'size': _size(unit)},
                                         lambda unit=unit: _unit(unit)))
            elif unit.missing:
                # its record says what it lacks, so what it is is decidable on sight (#721)
                out.append(cleaner.Entry('incomplete unit', unit.address.as_posix(),
                                         {'incomplete unit': f'missing {", ".join(unit.missing)}', 'size': _size(unit)},
                                         lambda unit=unit: _unit(unit)))
    return out


def clean(apply: bool) -> int:
    return cleaner.clean('stage', entries(), KINDS, corpus.stage_status, apply)


def main() -> int:
    args = command_parser('stage').parse_args()
    if args.verb == 'clean':
        return clean(bool(args.apply))
    return corpus.stage_status()


if __name__ == '__main__':
    sys.exit(main())
