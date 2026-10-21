#!/usr/bin/env python
"""reply.py - the launcher's reply to the reader (issues/896, issues/947): now:, the room's
standing read after the act, corpus-yoga status last, then the act's effect line, the last
line of every response an enacting verb gives. The standing is the fold of every noun's own
now:, read once and together (src/main/standing.py, issues/949); an act hands up no steps of
its own, so what its reply names is what the room's state allows after it.

The verb hands its effect up through facts.report, into the file the launcher named as
CORPUS_YOGA_EFFECT; this reads it back through the printer's own reader and says now:
once, from the room as the nouns read it now. A verb that handed nothing up - it crashed,
or exited before its effect - is said as NOT DONE with its exit code, so that a response
still ends on an effect line and the silence is legible.

Usage:
    src/run_python_script.sh src/main/reply.py <act> <effect-file> <exit-code>
"""
import sys
from pathlib import Path

SELF = 'src/main/reply.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_root[0] / 'src' / 'main'))
import facts  # noqa: E402
import standing  # noqa: E402 - the room's standing, the one fold


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
    shape = {'now': {**standing.room_now(), facts.ROOM.line: facts.ROOM.does}}
    print('\n'.join(facts.lines(facts.plain(shape), width=facts.terminal_width()) + [effect]), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
