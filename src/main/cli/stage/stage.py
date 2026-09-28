#!/usr/bin/env python
"""
stage.py (corpus-yoga stage) - the room's stage, tmp/stage, as the cache has its noun.

    corpus-yoga stage                   # status: the input, each orphan, each rehearsal, the units' counts
    corpus-yoga stage clean --dry-run   # what the janitor would remove: each rehearsal, each orphan, each unit held byte-equal
    corpus-yoga stage clean --apply     # remove it

The tier (src/main/tier.py, src/main/corpus.py): input is what the captures write, shared
by every rehearsal; rehearsal/<stamp> is what one rehearsal derived, named by its log's
stamp - evidence that stands until removed. The per-unit relations stay with each
capturing noun's bare status and with bare corpus-yoga pipeline; this face counts them
against the newest rehearsal. The janitor clears its tier as corpus-yoga cache clean clears
its own: every rehearsal, each named, and the rehearsals' directory once it holds none;
every staged unit the store holds byte-equal - a unit already promoted; and every entry
under tmp/stage that is neither the input nor a rehearsal, an orphan of an earlier layout.
A refused unit is evidence of another kind and is never the janitor's.

The janitor's lines keep their tenses: "will remove" before each act, "did" or "did NOT -
<why>" after it, so a log read after a crash shows the intention and, entry by entry,
whether it was carried out. An entry is removed as it stands at the act, not as it stood
at the naming: a directory that gained a file while being emptied is emptied again. The
tail is the verdict - DONE only when every named entry went, NOT DONE naming what was
NOT removed - and the apply ends by
relaying the bare status, the certified state after the act.
"""
import shutil
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
import corpus  # noqa: E402
import tier  # noqa: E402 — the tiers, one home (#702)

PASSES = 3   # the Finder writes into a directory being emptied; a second pass is the whole remedy


def _remove(path: Path) -> str | None:
    """Remove the entry as it stands at the act. None when it is gone, else why it is not."""
    why = 'still present'
    for _ in range(PASSES):
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif path.exists() or path.is_symlink():
                path.unlink()
        except OSError as e:
            why = (e.strerror or str(e)).lower()
        if not (path.exists() or path.is_symlink()):
            return None
    return why


PLURAL = {'rehearsal': 'rehearsals', 'orphan': 'orphans', 'unit held byte-equal': 'units held byte-equal'}


def _count(n: int, kind: str) -> str:
    return f'{n} {kind if n == 1 else PLURAL[kind]}'


def clean(apply: bool) -> int:
    entries: list[tuple[str, str, Path | corpus.Unit]] = []   # (kind, label, what to remove)
    for stamp in corpus.rehearsals():
        entries.append(('rehearsal', f'rehearsal {stamp} - the disposal of evidence: {corpus.rehearsal_header(stamp)}: '
                                     f'{corpus.human(corpus.size_of(tier.rehearsal(stamp)))}', tier.rehearsal(stamp)))
    for e in corpus.orphans():
        entries.append(('orphan', f'orphan {e.relative_to(REPO).as_posix()} - neither the input nor a rehearsal: '
                                  f'{corpus.human(corpus.size_of(e))}', e))
    if corpus.STAGE.is_dir():
        for unit in corpus.units(corpus.STAGE):
            if corpus.redundant(unit):
                entries.append(('unit held byte-equal', f'{unit.address}: held byte-equal in data/input', unit))
    kinds = ('rehearsal', 'orphan', 'unit held byte-equal')
    if not apply:
        for _kind, label, _what in entries:
            print(f'  would remove {label}')
        would = {kind: sum(1 for k, _, _ in entries if k == kind) for kind in kinds}
        print('stage clean: would remove ' + (', '.join(_count(would[kind], kind) for kind in kinds if would[kind]) or 'nothing')
              + (' (--apply removes them)' if entries else ''))
        return 0
    removed = {kind: 0 for kind in kinds}
    left: list[str] = []
    for kind, label, what in entries:
        print(f'  will remove {label}')
        if isinstance(what, corpus.Unit):
            try:
                corpus.remove(what)
                why = None
            except OSError as e:
                why = (e.strerror or str(e)).lower()
            name = str(what.address)
        else:
            why = _remove(what)
            name = what.relative_to(REPO).as_posix()
        if why is None:
            print('    did')
            removed[kind] += 1
        else:
            print(f'    did NOT - {why}')
            left.append(f'{kind}: {name} - {why}')
    # the rehearsals' directory goes with the last rehearsal: an empty directory is not data
    if tier.REHEARSALS.is_dir() and not any(tier.REHEARSALS.iterdir()):
        print(f'  will remove {tier.REHEARSALS.relative_to(REPO).as_posix()}, left empty')
        why = _remove(tier.REHEARSALS)
        print('    did' if why is None else f'    did NOT - {why}')
        if why is not None:
            left.append(f'{tier.REHEARSALS.relative_to(REPO).as_posix()} - {why}')
    did = ', '.join(_count(removed[kind], kind) for kind in kinds if removed[kind]) or 'nothing'
    if left:
        print(f'stage clean: NOT DONE - removed {did}; NOT removed ' + '; '.join(left))
    else:
        print(f'stage clean: DONE - removed {did}')
    # the noun's read-only status is the certified state after the act, informing and never gating
    print()
    corpus.stage_status()
    return 1 if left else 0


def main() -> int:
    args = command_parser('stage').parse_args()
    if args.verb == 'clean':
        return clean(bool(args.apply))
    return corpus.stage_status()


if __name__ == '__main__':
    sys.exit(main())
