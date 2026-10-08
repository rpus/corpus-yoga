"""
tier.py - the tiers as a declared contract (#702), the one home every script derives its
data and tmp paths from. Every script computes its code root, REPO, from its own address;
the only fact it lacks is which layout its tiers are read from, and that is one name:
CORPUS_YOGA_REHEARSAL, the stamp of a rehearsal, names the stage's scratch root under
TMP_STAGE, and unset names the checkout's. DATA_ROOT is that root, REPO or
tmp/stage/scratch, and DATA and TMP are its data and tmp. No path is ever
passed, only the name the layout resolves, so nothing but a rehearsal can rebind a tier.

The stage, TMP_STAGE, is the checkout's, a constant: TMP_STAGE_INPUT is what the captures
write; TMP_STAGE_SCRATCH holds only what the last rehearsal's run derived - data/input a
link to TMP_STAGE_INPUT, data/output its preview, tmp/cache its validation - and is
replaced whole by the next run; TMP_STAGE_REHEARSAL is the rehearsal record, one file,
what the last rehearsal saw and judged (src/main/rehearsal.py, #815). SCRATCH_TMP is the
scratch's tmp tier whatever tiers are in force, where the record reduces its verdicts from.
src/main/tier.sh is the shell twin. The dev gate holds that no other script under
src/main builds a data or tmp path from its root by hand.
"""
import os
from pathlib import Path

SELF = 'src/main/tier.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

TMP_STAGE = REPO / 'tmp' / 'stage'    # the checkout's stage, a constant
TMP_STAGE_INPUT = TMP_STAGE / 'input'  # what the captures write
TMP_STAGE_SCRATCH = TMP_STAGE / 'scratch'   # data/{input -> ../../input, output}, tmp/cache - the last run's, replaced whole
TMP_STAGE_REHEARSAL = TMP_STAGE / 'rehearsal.json'   # the rehearsal record, one file
SCRATCH_TMP = TMP_STAGE_SCRATCH / 'tmp'

REHEARSAL = os.environ.get('CORPUS_YOGA_REHEARSAL') or None
DATA_ROOT = TMP_STAGE_SCRATCH if REHEARSAL else REPO
DATA = DATA_ROOT / 'data'
TMP = DATA_ROOT / 'tmp'


def path(declared: str) -> Path:
    """A declared repo-relative path - data/..., tmp/... as the declarations and
    rsc/cache_io.csv spell them - under the tiers in force."""
    parts = Path(declared).parts
    if parts and parts[0] == 'data':
        return DATA.joinpath(*parts[1:])
    if parts and parts[0] == 'tmp':
        return TMP.joinpath(*parts[1:])
    return REPO.joinpath(*parts)
