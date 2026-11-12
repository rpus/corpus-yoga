"""reply.py - the launcher's reply to the reader (issues/896, issues/947, issues/951, issues/1016): the
bare status - what corpus-yoga status says, as it says it: what stands in the room's way,
then now:, the room's standing - and then the act's effect line, the last line of every
response an enacting verb gives. The reply composes nothing of its own: the status is the
one derivation of both, so a refused unit stands in every tail where it stands in the
status, above the verdict that names it.

The verb hands its effect up through facts.report, into the file the launcher named as
CORPUS_YOGA_EFFECT; this reads it back through the printer's own reader, asks the status
once, and says it. A verb that handed nothing up - it crashed, or exited before its effect
- is said as NOT DONE with its exit code, so that a response still ends on an effect line
and the silence is legible. A status that did not answer within the send bound is said as
now: unread, so that the tail still ends on now: and the effect.

Usage:
    src/run_python_script.sh src/main/reply.py <act> <effect-file> <exit-code>
"""
import os
import subprocess
import sys
from pathlib import Path
import enact
import facts
import tier

SELF = 'src/main/reply.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'

REPO = _root[0]


def status_said() -> list[str]:
    """What bare corpus-yoga status says, as lines, asked as the reader would type it - the
    act and its effect file withheld from its environment, within the send bound; or, as
    the one line the tail cannot lack, now: unread with why."""
    bound = enact.bound()
    environment = {k: v for k, v in os.environ.items() if k not in (tier.ACT, facts.EFFECT)}
    try:
        asked = subprocess.run([str(REPO / 'corpus-yoga'), 'status'], capture_output=True, text=True, cwd=REPO, timeout=bound, env=environment)
    except subprocess.TimeoutExpired:
        return facts.lines({'now': facts.phrase('unread - corpus-yoga {noun} did not answer within {bound} s', noun='status', bound=bound)})
    return asked.stdout.splitlines()


def main(argv: list[str]) -> int:
    act, path, code = argv[0], Path(argv[1]), int(argv[2])
    handed: dict = {}
    if path.is_file():
        read = facts.load(path.read_text())
        handed = read if isinstance(read, dict) else {}
        path.unlink()
    effect = handed.get('effect')
    if not isinstance(effect, str) or not effect:
        effect = f'{act}: {"DONE" if code == 0 else "NOT DONE"} - exit {code}; the verb handed up no effect line'
    print('\n'.join(status_said() + [effect]), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
