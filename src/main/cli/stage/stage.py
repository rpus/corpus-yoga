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

The janitor's lines keep their tenses: "will remove" before each act, "did" or "did NOT -
<why>" after it, so a log read after a crash shows the intention and, entry by entry,
whether it was carried out. An entry is removed as it stands at the act, not as it stood
at the naming: a directory that gained a file while being emptied is emptied again. The
tail is the verdict - DONE only when every named entry went, NOT DONE naming what was
NOT removed. The two faces are one derivation: one list of entries, one loop, the flag
deciding only whether the act runs after the line, so the dry run is the apply with the
act elided. The apply relays the bare status, the certified state after the act, beneath
its lines and above its verdict, which is its last line.
"""
import sys
from pathlib import Path
from typing import Callable

SELF = 'src/main/cli/stage/stage.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main'))
from declared_parser import command_parser  # noqa: E402
import corpus  # noqa: E402

KINDS = {'orphan': 'orphans', 'duplicate': 'duplicates', 'incomplete unit': 'incomplete units'}   # each kind of entry, and its plural


def _count(n: int, kind: str) -> str:
    return f'{n} {kind if n == 1 else KINDS[kind]}'


def _unit(unit: corpus.Unit) -> str | None:
    try:
        corpus.remove(unit)
    except OSError as e:
        return (e.strerror or str(e)).lower()
    return None


def entries() -> list[tuple[str, str, str, Callable[[], str | None]]]:
    """Everything the janitor acts on, in the order it acts: (kind, name, the line's
    label, the act). The one list both faces walk - the dry run is the apply with the act
    elided, so the two cannot disagree."""
    out: list[tuple[str, str, str, Callable[[], str | None]]] = []
    for e in corpus.orphans():
        name = e.relative_to(REPO).as_posix()
        out.append(('orphan', name, f'orphan {name} - neither the input nor a rehearsal: {corpus.human(corpus.size_of(e))}',
                    lambda e=e: corpus.dispose(e)))
    if corpus.STAGE.is_dir():
        for unit in corpus.units(corpus.STAGE):
            if corpus.redundant(unit):
                out.append(('duplicate', str(unit.address), f'{unit.address}: identical to the held unit',
                            lambda unit=unit: _unit(unit)))
            elif unit.missing:
                # its record says what it lacks, so what it is is decidable on sight (#721)
                out.append(('incomplete unit', str(unit.address), f'{unit.address}: incomplete - missing {", ".join(unit.missing)}',
                            lambda unit=unit: _unit(unit)))
    return out


def clean(apply: bool) -> int:
    """One loop over the one list; the flag decides only whether the act runs after the line."""
    did = {kind: 0 for kind in KINDS}
    left: list[str] = []
    for kind, name, label, act in entries():
        if not apply:
            print(f'  would remove {label}')
            did[kind] += 1
            continue
        print(f'  will remove {label}')
        why = act()
        if why is None:
            print('    did')
            did[kind] += 1
        else:
            print(f'    did NOT - {why}')
            left.append(f'{kind}: {name} - {why}')
    counts = ', '.join(_count(did[kind], kind) for kind in KINDS if did[kind]) or 'nothing'
    if not apply:
        print(f'stage clean: would remove {counts}' + (' (--apply removes them)' if counts != 'nothing' else ''))
        return 0
    # the noun's read-only status is the certified state after the act: evidence, beneath
    # the lines and above the verdict, informing and never gating
    print()
    corpus.stage_status()
    print()
    # one ask, one verdict, the last line
    if left:
        print(f'stage clean: NOT DONE - removed {counts}; NOT removed ' + '; '.join(left))
    else:
        print(f'stage clean: DONE - removed {counts}')
    return 1 if left else 0


def main() -> int:
    args = command_parser('stage').parse_args()
    if args.verb == 'clean':
        return clean(bool(args.apply))
    return corpus.stage_status()


if __name__ == '__main__':
    sys.exit(main())
