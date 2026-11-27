"""
tier.py - the tiers as a declared contract (issues/702), the one home every script derives its
machine-local paths from. Every script computes its code root, REPO, from its own address;
the only fact it lacks is which layout its tiers are read from, and that is one name:
CORPUS_YOGA_REHEARSAL, the stamp of a rehearsal, names the stage as the root, and unset names
the checkout's. DATA_ROOT is that root, REPO or stage/, and DATA,
CACHE, LOGS and TMP are its data, cache, logs and tmp. FETCH, what an outside source last
returned, is the room's whatever tiers are in force (issues/1170).

The stage, STAGE, is one directory, stage/ (issues/1171): every capture, rehearsal, promote and
clean. While the dev gate runs, CORPUS_YOGA_DEV_GATE names the directory it keeps its own data
under for the run - under tmp/, named for corpus-yoga test run and the run's pid - and the
stage and DATA_ROOT both resolve beneath it, so that no check reads or writes what the room's
acts produced (issues/1134). The stage is laid out as the checkout is (issues/1163): STAGE_INPUT,
its data/input, is what the captures write; its data/output, cache and logs are what the last
rehearsal's run derived, replaced whole by the next run; STAGE_TMP is that run's tmp, gone when
it ends; STAGE_REHEARSAL is the rehearsal record, one file, what the last rehearsal saw and
judged (src/main/rehearsal.py, issues/815). STAGE_CACHE is the stage's cache whatever tiers are
in force, where the record reduces its verdicts from.
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

DEV_GATE = Path(os.environ['CORPUS_YOGA_DEV_GATE']) if os.environ.get('CORPUS_YOGA_DEV_GATE') else None   # the dev gate's own data, while it runs
STAGE = (DEV_GATE or REPO) / 'stage'
STAGE_INPUT = STAGE / 'data' / 'input'  # what the captures write
STAGE_OUTPUT = STAGE / 'data' / 'output'   # the last rehearsal's run's, replaced whole
STAGE_CACHE = STAGE / 'cache'   # likewise
STAGE_TMP = STAGE / 'tmp'   # the rehearsal's run's working files, gone when it ends
STAGE_REHEARSAL = STAGE / 'rehearsal.json'   # the rehearsal record, one file
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
# a rehearsal's data, cache, logs and tmp are the stage's own; the dev gate's its own directory,
# the gate reading nothing the room's acts produce (issues/1134)
DATA_ROOT = STAGE if REHEARSAL else DEV_GATE or REPO
DATA = DATA_ROOT / 'data'
CACHE = DATA_ROOT / 'cache'
LOGS_ROOT = DATA_ROOT / 'logs'
TMP = DATA_ROOT / 'tmp'
REBOUND = ('data', 'cache', 'logs', 'tmp')   # the roots a rehearsal and the dev gate hold their own of
# where acts are logged: the room's act history, or - while the dev gate names the check whose acts
# it runs - beneath that check, under the gate run's own log, so what a room ran and what its gate
# ran are told apart (issues/1030)
LOGS = REPO / 'logs' / 'test' / 'run' / os.environ[GATE_CHECK] if os.environ.get(GATE_CHECK) else LOGS_ROOT


def cache_of(path) -> Path:
    """What the run derives from an input lives at the input's own address under cache/pipeline
    (issues/1192): the path under the input tree - the store's, or the stage's - re-rooted, a
    session's .jsonl dropped, so that an input and its outputs are one relative path under two roots."""
    path = Path(path)
    for root in (DATA / 'input', STAGE_INPUT):
        for under, base in ((path, root), (path.resolve(), root.resolve())):
            if under.is_relative_to(base):
                rel = under.relative_to(base)
                return CACHE / 'pipeline' / (rel.with_suffix('') if rel.suffix == '.jsonl' else rel)
    raise ValueError(f'{path} is under no input tree')


def path(declared: str) -> Path:
    """A declared repo-relative path - data/..., cache/..., logs/..., tmp/... as the
    declarations and rsc/cache_io.csv spell them - under the tiers in force; stage/... under the
    stage in force; fetch/... the room's whatever tiers are in force."""
    parts = Path(declared).parts
    if parts and parts[0] in REBOUND:
        return DATA_ROOT.joinpath(*parts)
    if parts and parts[0] == 'stage':
        return STAGE.joinpath(*parts[1:])
    return REPO.joinpath(*parts)
