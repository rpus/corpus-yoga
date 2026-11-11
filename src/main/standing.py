"""
standing.py - the room's standing, now:, folded once from every noun's own now: (issues/949).
Every noun whose declaration says `standing` says under now: what its own reading allows and
what it could not settle; this reads them once, together, and folds them - the one reading bare
corpus-yoga status says as its now: (src/main/cli/status/report.py), which the launcher's
reply says after every act (src/main/reply.py, issues/1016). No noun's status runs another,
and a noun that could not be read is said under its command, so that the fold hides no noun.
"""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import enact
import facts

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / 'src' / 'main' / 'cli'
# the nouns whose bare status ends on now:, as each declares `standing` (issues/1034)
NOUNS = tuple(sorted(d.parent.name for d in CLI.glob('*/*.json') if d.stem == d.parent.name and json.loads(d.read_text()).get('standing')))
_said: dict[str, object] = {}     # each noun's status, read once a process, however many spots are taken from it


def read_at_once(nouns) -> None:
    """Read the nouns' statuses together, so that the reading takes the time of the slowest
    and not their sum (issues/811): each is a process of its own, and none reads another."""
    with ThreadPoolExecutor(max_workers=max(1, len(nouns))) as pool:
        for noun in nouns:
            pool.submit(said_by, noun)


def said_by(noun: str):
    """What the noun's bare status says, loaded; or, in words, why it could not be read -
    within the send bound (enact.bound), since a status may send."""
    if noun not in _said:
        bound = enact.bound()
        try:
            asked = subprocess.run([str(REPO / 'corpus-yoga'), noun], capture_output=True, text=True, cwd=REPO, timeout=bound)
            _said[noun] = facts.load(asked.stdout)
        except subprocess.TimeoutExpired:
            _said[noun] = facts.phrase('unread - corpus-yoga {noun} did not answer within {bound} s', noun=noun, bound=bound)
        except ValueError as error:
            _said[noun] = facts.phrase('corpus-yoga {noun} is unreadable - {error}', noun=noun, error=error)
    return _said[noun]


def fold(nows: dict[str, object]) -> dict:
    """The fold of the nouns' now: blocks, each given by its noun, into one of the same shape
    (issues/1050): every act of a block under its modality and its own command; a noun whose
    now: is a sentence other than none, or whose status could not be read, under MAY and its
    command. Empty where every noun says none."""
    out: dict = {}
    for noun, now in nows.items():
        if isinstance(now, dict):
            facts.merge(out, now, once=True)   # an act two nouns name over one unit is one act (issues/1028)
        elif isinstance(now, str) and now != facts.phrase('none - nothing to do'):
            facts.merge(out, {'MAY': {f'corpus-yoga {noun}': {facts.REPORTS: {now: 1}}}}, once=True)
    return facts.ordered(out)


def failing(said):
    """What of a noun's status is a finding: each FAIL's words, under the keys that lead to it;
    None where it holds none. A noun's now: holds acts, never a finding."""
    if not isinstance(said, dict):
        return None
    if 'FAIL' in said:
        return said['FAIL']
    kept = {key: found for key, value in said.items() if key != 'now' and (found := failing(value)) is not None}
    return kept or None


def room_fail() -> dict:
    """Every finding the nouns hold, each noun's under its command (issues/1058): the room's
    FAIL:, gathered from the statuses the fold already read."""
    read_at_once(NOUNS)
    return {f'corpus-yoga {noun}': found for noun in NOUNS if (found := failing(said_by(noun))) is not None}


def room_now() -> dict:
    """The room's standing: the nouns read once, together, and their now: folded."""
    read_at_once(NOUNS)
    nows: dict[str, object] = {}
    for noun in NOUNS:
        said = said_by(noun)
        nows[noun] = said.get('now') if isinstance(said, dict) else said
    return fold(nows)
