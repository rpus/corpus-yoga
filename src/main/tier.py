"""
tier.py - the tiers as a declared contract (#702), the one home every script derives its
data and tmp paths from. Every script computes its code root, REPO, from its own address;
the only fact it lacks is which layout its tiers are read from, and that is one name:
CORPUS_YOGA_REHEARSAL, the stamp of a rehearsal, names the rehearsal's own root under
TMP_STAGE, and unset names the checkout's. DATA_ROOT is that root, REPO or
tmp/stage/rehearsal/<stamp>, and DATA and TMP are its data and tmp. No path is ever
passed, only the name the layout resolves, so nothing but a rehearsal can rebind a tier.

The stage, TMP_STAGE, is the checkout's, a constant: TMP_STAGE_INPUT is what the captures write,
shared by every rehearsal, and each rehearsal under REHEARSALS holds only what it derived -
data/input a link to TMP_STAGE_INPUT, data/output its preview, tmp/cache its verdicts.
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
REHEARSALS = TMP_STAGE / 'rehearsal'       # <stamp>/data/{input -> ../../../input, output}, <stamp>/tmp/cache

REHEARSAL = os.environ.get('CORPUS_YOGA_REHEARSAL') or None
DATA_ROOT = REHEARSALS / REHEARSAL if REHEARSAL else REPO
DATA = DATA_ROOT / 'data'
TMP = DATA_ROOT / 'tmp'


def rehearsal(stamp: str) -> Path:
    return REHEARSALS / stamp


def newest_rehearsal() -> str | None:
    """The stamp of the newest rehearsal, or None: the stamp is a label whose lexical order
    is the stamping order; order and currency between rehearsals are the records' digests."""
    stamps = sorted(d.name for d in REHEARSALS.iterdir() if d.is_dir()) if REHEARSALS.is_dir() else []
    return stamps[-1] if stamps else None


def path(declared: str) -> Path:
    """A declared repo-relative path - data/..., tmp/... as the declarations and
    rsc/cache_io.csv spell them - under the tiers in force."""
    parts = Path(declared).parts
    if parts and parts[0] == 'data':
        return DATA.joinpath(*parts[1:])
    if parts and parts[0] == 'tmp':
        return TMP.joinpath(*parts[1:])
    return REPO.joinpath(*parts)
