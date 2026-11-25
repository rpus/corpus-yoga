"""
tier.py - the tiers as a declared contract (issues/702), the one home every script derives its
machine-local paths from. Every script computes its code root, REPO, from its own address;
the only fact it lacks is which layout its tiers are read from, and that is one name:
CORPUS_YOGA_REHEARSAL, the stamp of a rehearsal, names the stage's scratch root under
STAGE, and unset names the checkout's. DATA_ROOT is that root, REPO or
stage/<actor>/scratch, and DATA, CACHE, LOGS and TMP are its data, cache, logs and tmp. No path
is ever passed, only the name the layout resolves, so nothing but a rehearsal can rebind a tier.
FETCH, what an outside source last returned, and the stage are the room's whatever tiers are in
force (issues/1170).

The stage, STAGE, is an actor's, under stage/, named for the actor (issues/1133): the usr
actor's, stage/usr, every capture, rehearsal, promote and clean, wherever CORPUS_YOGA_ACTOR
names no other - the dev actor's, stage/dev, being the one other. STAGE_INPUT is what the captures
write; STAGE_SCRATCH holds only what the last rehearsal's run derived - data/input a
link to STAGE_INPUT, data/output its preview, cache its validation - and is
replaced whole by the next run; STAGE_REHEARSAL is the rehearsal record, one file,
what the last rehearsal saw and judged (src/main/rehearsal.py, issues/815). SCRATCH_CACHE is the
scratch's cache whatever tiers are in force, where the record reduces its verdicts from.
src/main/tier.sh is the shell twin. The dev gate holds that no other script under
src/main builds a machine-local path from its root by hand.
"""
import os
from pathlib import Path

SELF = 'src/main/tier.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

ACTORS = ('usr', 'dev')   # whose a stage is, each its own under stage/
ACTOR = os.environ.get('CORPUS_YOGA_ACTOR') or 'usr'
assert ACTOR in ACTORS, f'CORPUS_YOGA_ACTOR names {ACTOR!r}, no actor of {ACTORS}'
STAGE = REPO / 'stage' / ACTOR    # the actor's stage
STAGE_INPUT = STAGE / 'input'  # what the captures write
STAGE_SCRATCH = STAGE / 'scratch'   # data/{input -> ../../input, output}, cache - the last run's, replaced whole
STAGE_REHEARSAL = STAGE / 'rehearsal.json'   # the rehearsal record, one file
SCRATCH_CACHE = STAGE_SCRATCH / 'cache'
FETCH = REPO / 'fetch'    # what an outside source last returned; a fetch remakes it

REHEARSAL = os.environ.get('CORPUS_YOGA_REHEARSAL') or None
ACT = 'CORPUS_YOGA_ACT'       # the launcher names the act it dispatched, `<command> <verb>` (issues/896)
STAMP = 'CORPUS_YOGA_STAMP'   # the stamp of that act, so the act's own artifacts share it (issues/708)
LOG = 'CORPUS_YOGA_LOG'       # and the record it tees the whole act into, logs/<command>/<verb>/<stamp>.log
DECLARATION = 'CORPUS_YOGA_DECLARATION'   # the declaration the launcher dispatched, as send.dispatched hands it - whose sends a script may run (issues/1022, issues/1036)
GATE_CHECK = 'CORPUS_YOGA_GATE_CHECK'   # the dev gate names the check whose acts it runs, `<gate run>/<check>` (issues/1030)


def dispatched(act: str) -> bool:
    """Whether the launcher dispatched this act, `<command> <verb>` - the one case in which
    the stamp and the record it names are this verb's own. A verb another verb runs inherits
    the names and must not take them (issues/912)."""
    return os.environ.get(ACT) == act


def stamp_of(act: str) -> str:
    """The act's stamp: the launcher's where it dispatched the act, a fresh one otherwise -
    the one reading of CORPUS_YOGA_STAMP (issues/912)."""
    import time
    return (os.environ.get(STAMP) if dispatched(act) else None) or time.strftime('%Y-%m-%dT%H%M%SZ', time.gmtime())


def record_of(act: str) -> Path | None:
    """The act's record, the launcher's tee, where the launcher dispatched the act; None
    otherwise - the one reading of CORPUS_YOGA_LOG (issues/912). No verb writes into it."""
    named = os.environ.get(LOG) if dispatched(act) else None
    return Path(named) if named else None
# a rehearsal's data, cache, logs and tmp are its stage's scratch; so are the dev actor's always,
# the dev gate reading nothing the usr actor's acts produce (issues/1134)
DATA_ROOT = STAGE_SCRATCH if REHEARSAL or ACTOR == 'dev' else REPO
DATA = DATA_ROOT / 'data'
CACHE = DATA_ROOT / 'cache'
LOGS_ROOT = DATA_ROOT / 'logs'
TMP = DATA_ROOT / 'tmp'
REBOUND = ('data', 'cache', 'logs', 'tmp')   # the roots a rehearsal and the dev gate hold their own of
# where acts are logged: the room's act history, or - while the dev gate names the check whose acts
# it runs - beneath that check, under the gate run's own log, so what a room ran and what its gate
# ran are told apart (issues/1030)
LOGS = REPO / 'logs' / 'test' / 'run' / os.environ[GATE_CHECK] if os.environ.get(GATE_CHECK) else LOGS_ROOT


def path(declared: str) -> Path:
    """A declared repo-relative path - data/..., cache/..., logs/..., tmp/... as the
    declarations and rsc/cache_io.csv spell them - under the tiers in force; fetch/... and
    stage/... are the room's whatever tiers are in force."""
    parts = Path(declared).parts
    if parts and parts[0] in REBOUND:
        return DATA_ROOT.joinpath(*parts)
    return REPO.joinpath(*parts)
