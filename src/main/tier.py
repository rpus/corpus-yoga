"""
tier.py - the tiers as a declared contract (#702): DATA and TMP, each a variable with the
checkout's own tier as its default, the one home every script derives its data and tmp
paths from. CORPUS_YOGA_DATA and CORPUS_YOGA_TMP name other tiers; corpus-yoga pipeline
rehearse runs the checkout's own code over the stage's, tmp/stage/data and tmp/stage/tmp.
The stage itself is the checkout's, never a tier variable's: STAGE is where the captures
write (STAGE_DATA/input) and a rehearsal derives (STAGE_TMP/cache) and projects
(STAGE_DATA/output). src/main/tier.sh is the shell twin. The dev gate holds that no other
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
STAGE_DATA = STAGE / 'data'
STAGE_TMP = STAGE / 'tmp'


def path(declared: str) -> Path:
    """A declared repo-relative path - data/..., tmp/... as the declarations and
    rsc/cache_io.csv spell them - under the tiers in force."""
    parts = Path(declared).parts
    if parts and parts[0] == 'data':
        return DATA.joinpath(*parts[1:])
    if parts and parts[0] == 'tmp':
        return TMP.joinpath(*parts[1:])
    return REPO.joinpath(*parts)
