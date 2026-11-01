"""
standing.py - the room's standing, now:, folded once from every noun's own now: (issues/949).
Store, forge, cache, logs, server, site and pipeline each say under now: what their own reading
allows; this reads the seven once, together, and folds them - the one reading bare
corpus-yoga status says as its now: (src/main/cli/status/report.py) and the launcher's
reply says after every act (src/main/reply.py). No noun's status runs another, and a noun
that could not be read is said under its command, so that the fold hides no noun.
"""
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import enact
import facts

REPO = Path(__file__).resolve().parents[2]
NOUNS = ('store', 'forge', 'cache', 'logs', 'server', 'site', 'pipeline')   # the nouns whose status ends on now:
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
    """The fold of the nouns' now: blocks, each given by its noun: every command of a block
    under its own command; a noun whose now: is a sentence other than none, or whose
    status could not be read, under its command. Empty where every noun says none."""
    out: dict = {}
    for noun, now in nows.items():
        if isinstance(now, dict):
            out.update(now)
        elif isinstance(now, str) and now != facts.phrase('none - nothing to do'):
            out[f'corpus-yoga {noun}'] = {'reports the noun': {now: 1}}
    return out


def room_now() -> dict:
    """The room's standing: the six nouns read once, together, and their now: folded."""
    read_at_once(NOUNS)
    nows: dict[str, object] = {}
    for noun in NOUNS:
        said = said_by(noun)
        nows[noun] = said.get('now') if isinstance(said, dict) else said
    return fold(nows)
