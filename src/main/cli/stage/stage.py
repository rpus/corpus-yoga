#!/usr/bin/env python
"""
stage.py (corpus-yoga stage) - the room's stage, tmp/stage, as the cache has its noun.

    corpus-yoga stage                   # status: each subtree and its size, the last rehearsal, the units' counts
    corpus-yoga stage clean --dry-run   # what the janitor would remove: each rehearsal by name, each unit held byte-equal
    corpus-yoga stage clean --apply     # remove it

The tier (src/main/tier.py, src/main/corpus.py): input is what the captures write, shared
by every rehearsal; rehearsal/<stamp> is what one rehearsal derived, named by its log's
stamp - evidence that stands until removed. The per-unit relations stay with each
capturing noun's bare status and with bare corpus-yoga pipeline; this face counts them
against the newest rehearsal. The janitor removes every rehearsal, each named, and every
staged unit the store holds byte-equal - a unit already promoted; a refused unit is
evidence of another kind and stays until the reader removes it by hand.
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

TIER = tier.STAGE
LOGS = tier.TMP / 'logs' / 'pipeline' / 'rehearse'   # each rehearsal's log, its record, by the same stamp


def _size(p: Path) -> int:
    if p.is_file() or p.is_symlink():
        return p.lstat().st_size
    return sum(f.lstat().st_size for f in p.rglob('*') if f.is_file() or f.is_symlink())


def _human(n: float) -> str:
    for unit in ('B', 'K', 'M', 'G'):
        if n < 1024:
            return f'{n:.0f}{unit}'
        n /= 1024
    return f'{n:.1f}T'


def _header(stamp: str) -> str:
    """The rehearsal's record: its log's header - time, room, commit - and the command as typed."""
    log = LOGS / f'{stamp}.log'
    if not log.is_file():
        return 'no log under tmp/logs/pipeline/rehearse - run by path, not by the launcher'
    return ' · '.join(log.read_text().splitlines()[:2])


def rehearsals() -> list[str]:
    return sorted(d.name for d in tier.REHEARSALS.iterdir() if d.is_dir()) if tier.REHEARSALS.is_dir() else []


def status() -> int:
    if not TIER.is_dir():
        print('tmp/stage/: absent - nothing captured since the last clean, no rehearsal made')
        return 0
    print(f'tmp/stage/: input {_human(_size(tier.STAGE_INPUT)) if tier.STAGE_INPUT.exists() else "absent"}')
    stamps = rehearsals()
    if not stamps:
        print('  rehearsals: none - corpus-yoga pipeline rehearse makes one')
    for stamp in stamps:
        print(f'  rehearsal {stamp} ({_human(_size(tier.rehearsal(stamp)))}): {_header(stamp)}')
    rows = corpus.survey()
    if not rows:
        print('  units: none staged')
        return 0
    held = sum(1 for u, rel, _d, ok, _w in rows if corpus.promotable(rel, ok) and corpus.redundant(u))
    promotable = sum(1 for u, rel, _d, ok, _w in rows if corpus.promotable(rel, ok)) - held
    refused = len(rows) - held - promotable
    print(f'  units: {len(rows)} staged - {promotable} promotable, {held} held already (byte-equal), {refused} refused'
          + (f', judged by rehearsal {stamps[-1]}' if stamps else '') + '; the relations: corpus-yoga pipeline, or each capturing noun bare')
    return 0


def clean(apply: bool) -> int:
    doomed: list[tuple[str, Path]] = []
    for stamp in rehearsals():
        doomed.append((f'rehearsal {stamp} - the disposal of evidence: {_header(stamp)}', tier.rehearsal(stamp)))
    units = [u for u in corpus.units(corpus.STAGE) if corpus.redundant(u)] if corpus.STAGE.is_dir() else []
    if not doomed and not units:
        print('stage clean: DONE - nothing to remove')
        return 0
    verb = 'removed' if apply else 'would remove'
    for label, path in doomed:
        print(f'  {verb} {label}: {_human(_size(path))}')
        if apply:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
    for unit in units:
        print(f'  {verb} {unit.address}: held byte-equal in data/input')
        if apply:
            corpus.remove(unit)
    print(f'stage clean: {"DONE" if apply else "would"} - {len(doomed)} rehearsal(s), {len(units)} unit(s) held byte-equal'
          + ('' if apply else ' (--apply removes them)'))
    return 0


def main() -> int:
    args = command_parser('stage').parse_args()
    if args.verb == 'clean':
        return clean(bool(args.apply))
    return status()


if __name__ == '__main__':
    sys.exit(main())
