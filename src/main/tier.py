"""
tier.py - the tiers as a declared contract (#702): DATA and TMP, each a variable with the
checkout's own tier as its default, the one home every script derives its data and tmp
paths from. CORPUS_YOGA_DATA and CORPUS_YOGA_TMP name other tiers; corpus-yoga pipeline
rehearse runs the checkout's own code over a rehearsal's own, under tmp/stage/rehearsal/<stamp>.
The stage itself is the checkout's, never a tier variable's: STAGE_INPUT is what the
captures write, shared by every rehearsal, and each rehearsal has a directory of its own
under REHEARSALS, named by its stamp - the key its log under tmp/logs/pipeline/rehearse
carries - holding only what it derived: a data tier whose input is a link to STAGE_INPUT
and whose output is its preview, and a tmp tier with its cache. src/main/tier.sh is the
shell twin. The dev gate holds that no other
script under src/main builds a data or tmp path from its root by hand.
"""
import os
from pathlib import Path

SELF = 'src/main/tier.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

DATA = Path(os.environ.get('CORPUS_YOGA_DATA') or REPO / 'data')
TMP = Path(os.environ.get('CORPUS_YOGA_TMP') or REPO / 'tmp')
STAGE = REPO / 'tmp' / 'stage'
STAGE_INPUT = STAGE / 'input'          # what the captures write
REHEARSALS = STAGE / 'rehearsal'       # <stamp>/data/{input -> ../../input, output}, <stamp>/tmp/cache


def rehearsal(stamp: str) -> Path:
    return REHEARSALS / stamp


def newest_rehearsal() -> str | None:
    """The stamp of the newest rehearsal, or None: the stamp is a label whose lexical order
    is the launcher's stamping order; order and currency between rehearsals are the
    records' digests."""
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
