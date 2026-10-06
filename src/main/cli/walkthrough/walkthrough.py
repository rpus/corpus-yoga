#!/usr/bin/env python
"""
walkthrough.py - `corpus-yoga walkthrough`: the room's state as one tree, walked by the
reader (#766). The walk starts on the top, which holds the commands, the machine report
first. Under each stand its status, where it has one - what its bare status prints,
loaded when the walk lands on it: the lines are the data (#753), so the walk has no
second interface to any noun - and its help: its declaration, as it states it (#770). So
help is read as the state is, with the same keys, and what does not vary with the room
is read beside what does. Five keys work it, the bottom row of the keyboard, and a sixth
leaves:

  x  run      the command the walk stands on, in the foreground; the state is read again after
  v  value    shows the value the walk stands on
  b  back     over the last move
  n  next     the next sibling at this depth
  m  members  into the node the walk stands on: its first key, or its first value
  q  quit

A key is the head of what it holds, and a step says the head alone (#787): the key, and
the size and shape of what stands beneath it, each under the name of the key that would
bring it - `members:` so many keys or so many values, for m; `value:` so many words, for
v, and after v the value itself; `next:` the sibling n goes to - never the thing itself,
so the reader chooses knowing what follows and no step scrolls. A line that is absent is
a key with nothing to bring. A status that cannot be read is no content: the step says
`FAIL:` and why. Every spot has an address, its JSON pointer (RFC 6901) from the top of the tree - a `/`
before each key, `~1` for a slash within one and `~0` for a tilde, a bare value by its
place in its list (#775). A step says the spot's pointer; `corpus-yoga walkthrough
<pointer>` starts there, reading what the pointer passes through - typed bare, a pointer
with a space in a key arrives as several words, and they are read as one; and on leaving
the walk says the command that continues from where it left, quoted for the shell.

The exit says whether the walk went as asked (#782), so a caller can chain on it:
  0  it stood where it was asked, and what it ran succeeded
  1  a command run with x failed, or a status the walk landed on could not be read
  2  the argument is no pointer: refused, and no walk
  3  the pointer names no spot: the walk started on the longest truncation of it that stands

A key is read from the terminal as it is pressed, or as a
line on stdin, so a model or a test walks as a reader does. Each step is said as facts,
one YAML document per step, and the mark between two steps is the key that made the
second - `-n-`, `-m-`, `-v-`, `-b-`, `-x-`, `-q-` - so the transcript is its own history. The
walk needs nothing outside the standard library: before the venv exists it has one noun,
the machine report, whose remedies are the first steps.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SELF = 'src/main/cli/walkthrough/walkthrough.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import facts  # noqa: E402

CLI = REPO / 'src' / 'main' / 'cli'
REPORT = 'prerequisites'                              # the machine report: the first noun, and the one that runs before the venv
REPORT_SCRIPT = './src/main/cli/prerequisites/prerequisites.sh'
FIRST = (REPORT, 'stage', 'store')                    # the room's state, in the order a reader meets it
TOP = 'corpus-yoga'                                   # the key of the top, the one spot with no pointer token
KEYS = 'n next, m members, v value, b back, x run, q quit'
UNREAD = object()                                     # a noun whose status the walk has not yet read
FAILED, REFUSED, GONE = 1, 2, 3                       # the walk's exits where it did not go as asked


def venv() -> bool:
    return (Path(os.environ.get('VENV', Path.home() / 'venvs' / 'general')) / 'bin' / 'python').is_file()


def nouns() -> list[str]:
    """Every declared command, the room's state first."""
    declared = sorted(d.name for d in CLI.iterdir() if (d / f'{d.name}.json').is_file())
    return [n for n in FIRST if n in declared] + [n for n in declared if n not in FIRST]


def reports(noun: str) -> bool:
    """Whether the command has a bare status: it declares a verb beside itself."""
    return any(f.stem != noun for f in (CLI / noun).glob('*.json'))


EFFECT = {'r': 'reads', 'w': 'writes', 'consumes': 'consumes', 'x': 'runs', 'sends': 'sends'}   # a declaration's effects, in words


def said(declared: dict, summary: str) -> dict:
    """One declaration as the walk shows it: what it is, what its things are, its
    arguments each with its help, and its effects."""
    out: dict = {'summary': declared.get(summary, '')}
    if declared.get('explanation'):
        out['explanation'] = declared['explanation']
    arguments = {a['name']: a['help'] for a in declared.get('args', [])}
    if arguments:
        out['arguments'] = arguments
    out.update({word: declared[key] for key, word in EFFECT.items() if declared.get(key)})
    return out


def help_of(noun: str) -> dict:
    """A command's help: its declaration, then each verb's beneath its name."""
    out = said(json.loads((CLI / noun / f'{noun}.json').read_text()), 'summary')
    verbs = {f.stem: said(json.loads(f.read_text()), 'help') for f in sorted((CLI / noun).glob('*.json')) if f.stem != noun}
    if verbs:
        out['verbs'] = verbs
    return out


def room() -> dict:
    """The tree before anything is read: each command's status unread, its help beside it."""
    return {noun: ({'status': UNREAD} if reports(noun) else {}) | {'help': help_of(noun)} for noun in nouns()}


@dataclass(frozen=True)
class Unreadable:
    """A status the walk could not read, and why. It stands where the status would, and is
    no content: a step says it as a FAIL."""
    why: str


def status(noun: str):
    """A noun's facts: what its bare status prints, loaded - or why it cannot be read."""
    if not venv() and noun != REPORT:
        return Unreadable(f'the venv is not minted, so corpus-yoga {noun} cannot be asked - /{REPORT}/status says how to mint it')
    command = [str(REPO / 'corpus-yoga'), noun] if venv() else [REPORT_SCRIPT]
    asked = subprocess.run(command, capture_output=True, text=True, cwd=REPO)
    try:
        loaded = facts.load(asked.stdout)
    except ValueError as error:
        return Unreadable(f'what corpus-yoga {noun} printed does not load - {error}')
    if isinstance(loaded, dict):
        loaded.pop('usage', None)                     # the CLI's tail, not the noun's state
    return loaded if loaded else Unreadable(f'corpus-yoga {noun} said nothing (exit {asked.returncode})')


def pointer_of(tokens: list[str]) -> str:
    """The JSON pointer of a path of tokens (RFC 6901)."""
    return ''.join('/' + token.replace('~', '~0').replace('/', '~1') for token in tokens)


def tokens_of(pointer: str) -> list[str]:
    """A JSON pointer's tokens; the empty pointer, the whole tree, has none."""
    if pointer in ('', '/'):
        return []
    if not pointer.startswith('/'):
        raise ValueError(f'{pointer!r} is no JSON pointer - one begins with /')
    return [token.replace('~1', '/').replace('~0', '~') for token in pointer[1:].split('/')]


def command_of(key: str) -> list[str] | None:
    """The key as a command the walk can run: corpus-yoga and a declared command, or the
    machine report's own script, the one command there is before the launcher works. A
    placeholder the reader must fill makes it theirs to type."""
    if '<' in key:
        return None
    try:
        words = shlex.split(key)
    except ValueError:
        return None                                   # an apostrophe in a sentence: no command line
    if not words:
        return None
    if words[0] == REPORT_SCRIPT:
        return words
    if words[0].removeprefix('./') == 'corpus-yoga' and len(words) > 1 and (CLI / words[1] / f'{words[1]}.json').is_file():
        return [str(REPO / 'corpus-yoga'), *words[1:]]
    return None


@dataclass
class Step:
    """Where the walk stands, and what each key would bring from there: a line is named
    for its key, and is absent where the key has nothing to bring."""
    at: str                                           # the spot's address: its JSON pointer from the top
    key: str
    members: str | None = None                        # what m goes into: so many keys, or so many values - never the things
    value: object = None                              # what v shows: its size, and once v has asked, the value
    FAIL: str | None = None                           # why the status that would stand here could not be read
    following: str | None = facts.named('next', default=None)   # the sibling n goes to
    runs: str | None = None                           # what x would run, where the key is a command
    note: str | None = None                           # why the last key moved nothing
    keys: str | None = None


@dataclass
class Ran:
    ran: str
    exit: int


@dataclass
class Left:
    """Where the walk left, and the command that continues from there."""
    at: str

    def facts(self) -> dict:
        if not self.at:                               # the top: the walk started bare stands there
            return {'walkthrough': 'left at the top', 'corpus-yoga walkthrough': 'continues from there'}
        return {'walkthrough': f'left at {self.at}', f'corpus-yoga walkthrough {shlex.quote(self.at)}': 'continues from there'}


@dataclass
class Walk:
    """The tree, and the walk's place in it: the path of keys from the top."""
    tree: dict = field(default_factory=dict)
    path: list[str] = field(default_factory=list)
    history: list[tuple[list[str], bool]] = field(default_factory=list)
    shown: bool = False                               # whether v has asked for the value the walk stands on
    failed: bool = False                              # whether a command run with x has failed, or a status could not be read

    def __post_init__(self):
        self.tree = room()
        self.path = []                                # the top

    def node(self, path: list[str], read: bool = False):
        """What stands at the path. A status is read where the path passes through it, or
        ends on it and `read` asks - the walk lands there; a status only beside or beneath
        the walk's way stays unread, so starting the walk runs nothing."""
        at = self.tree
        for depth, key in enumerate(path):
            if isinstance(at, (list, Unreadable)):
                return None
            if at[key] is UNREAD and (read or depth + 1 < len(path)):
                at[key] = status(path[0])
            at = at[key]
        return at

    def address(self, path: list[str] | None = None) -> str:
        """The spot's JSON pointer: each key, and a bare value by its place in its list."""
        path = self.path if path is None else path
        tokens = []
        for depth, key in enumerate(path):
            parent = self.node(path[:depth])
            tokens.append(str([str(item) for item in parent].index(key)) if isinstance(parent, list) else key)
        return pointer_of(tokens)

    def seek(self, pointer: str) -> str | None:
        """Stand on the spot the pointer names, reading what it passes through. Where no
        such spot stands: on the longest truncation of the pointer that names one - its
        leading segments, as far as each is there - with the note that says so. An
        argument that is no pointer is the caller's to mend, and raises."""
        tokens = tokens_of(pointer)
        path: list[str] = []
        for token in tokens:
            here = self.node(path, read=True) if path else self.tree
            if isinstance(here, dict) and token in here:
                path.append(token)
            elif isinstance(here, list) and token.isdigit() and int(token) < len(here):
                path.append(str(here[int(token)]))
            else:
                break
        self.path = path
        return None if len(path) == len(tokens) else f'no spot stands at {pointer} - the longest part of it that stands is {self.address() or "the top"}'

    def siblings(self) -> list[str]:
        if not self.path:
            return []
        parent = self.node(self.path[:-1])
        if isinstance(parent, list):
            return [str(item) for item in parent]
        return list(parent) if isinstance(parent, dict) else []

    def children(self) -> list[str] | None:
        """The keys beneath the node; None where it holds one value. Entering a status reads it."""
        here = self.node(self.path, read=True)
        if isinstance(here, dict):
            return list(here)
        return [str(item) for item in here] if isinstance(here, list) else None

    def leaf(self) -> bool:
        """Whether the walk stands on a key that holds one value."""
        here = self.node(self.path, read=True)
        return bool(self.path) and not isinstance(here, (dict, list, Unreadable)) and isinstance(self.node(self.path[:-1]), dict)

    def move(self, key: str) -> str | None:
        """Take one key; the note where it moved nothing."""
        if key == 'n':
            if not self.path:
                return 'the top has no next - m goes into its members'
            around = self.siblings()
            place = around.index(self.path[-1])
            if place + 1 == len(around):
                return 'this is the last here - b goes back'
            self.history.append((list(self.path), self.shown))
            self.path[-1], self.shown = around[place + 1], False
        elif key == 'm':
            beneath = self.children()
            if not beneath:
                return 'no members here - ' + ('v shows the value' if self.leaf() and not self.shown else 'n goes on, b goes back')
            self.history.append((list(self.path), self.shown))
            self.path.append(beneath[0])
            self.shown = False
        elif key == 'v':
            if not self.leaf():
                return 'no value here - ' + ('m goes into its members' if self.children() else 'n goes on, b goes back')
            if self.shown:
                return 'the value is shown - n goes on, b goes back'
            self.history.append((list(self.path), self.shown))
            self.shown = True
        elif key == 'b':
            if not self.history:
                return 'the walk began here'
            self.path, self.shown = self.history.pop()
        else:
            return f'{key!r} is no key - {KEYS}'
        return None

    def step(self, note: str | None = None, keys: bool = False) -> Step:
        around = self.siblings()
        key = self.path[-1] if self.path else TOP
        here = self.node(self.path, read=True)        # the walk lands here: a status is read now
        members = value = fail = None
        if isinstance(here, Unreadable):
            fail, self.failed = here.why, True
        elif isinstance(here, dict):
            members = f'{len(here)} key' + ('' if len(here) == 1 else 's')
        elif isinstance(here, list):
            members = f'{len(here)} value' + ('' if len(here) == 1 else 's')
        elif self.leaf():
            words = len(str(here).split())
            value = here if self.shown else f'{words} word' + ('' if words == 1 else 's')
        place = around.index(key) if self.path else 0
        command = command_of(key) if self.path else None
        return Step(self.address(), key, members=members, value=value, FAIL=fail,
                    following=around[place + 1] if place + 1 < len(around) else None,
                    runs='x - ' + ' '.join(key.split()) if command else None,
                    note=note, keys=KEYS if keys else None)

    def run(self) -> Ran | str:
        """Run the command the walk stands on, in the foreground, then forget what was read."""
        command = command_of(self.path[-1]) if self.path else None
        if command is None:
            return 'no command stands here - x runs a key that is a corpus-yoga command' + (
                '; this one holds a placeholder, and is the reader\'s to type' if self.path and '<' in self.path[-1] else '')
        sys.stdout.flush()
        done = subprocess.run(command, cwd=REPO)
        self.tree = room()
        self.history.clear()
        self.shown = False
        while len(self.path) > 1 and not self._stands():
            self.path.pop()                           # the state moved: stand on what is left of the path
        self.failed = self.failed or done.returncode != 0
        return Ran(' '.join(self.path[-1].split()) if command_of(self.path[-1]) else ' '.join(command[1:]), done.returncode)

    def _stands(self) -> bool:
        try:
            parent = self.node(self.path[:-1])
        except (KeyError, TypeError):
            return False
        return isinstance(parent, (dict, list)) and self.path[-1] in ([str(i) for i in parent] if isinstance(parent, list) else parent)


class Keys:
    """The reader's keys, one at a time: each as it is pressed at a terminal, else each
    line of stdin - its first letter - so a script walks as a reader does. At a terminal
    the keys are taken unbuffered and nothing typed ahead is dropped; `cooked` hands the
    terminal back as it was found, for a command run in the foreground."""

    def __init__(self):
        self.terminal = sys.stdin.isatty()
        self.saved = None
        if self.terminal:
            import termios
            import tty
            self.saved = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno(), termios.TCSANOW)

    def __iter__(self):
        if self.terminal:
            while True:
                key = sys.stdin.read(1)
                if not key:
                    return
                if key.strip():
                    yield key
        else:
            for line in sys.stdin:
                if line.strip():
                    yield line.strip()[0]

    def restore(self) -> None:
        if self.saved is not None:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, self.saved)

    def unbuffer(self) -> None:
        if self.saved is not None:
            import termios
            import tty
            tty.setcbreak(sys.stdin.fileno(), termios.TCSANOW)


def main() -> int:
    walk = Walk()
    # a pointer typed bare is split by the shell at each space within a key: its words are one pointer
    words = [argument for argument in sys.argv[1:] if not argument.startswith('-')]
    try:
        astray = walk.seek(' '.join(words)) if words else None
    except ValueError as error:
        print(f'walkthrough: NOT DONE - {error}', file=sys.stderr)
        return REFUSED
    keys = Keys()
    try:
        facts.say(walk.step(astray, keys=True))
        sys.stdout.flush()
        left = 'q'                                        # the key the walk ended on; the end of stdin leaves as q does
        for key in keys:
            if key == 'q':
                break
            print(f'-{key}-')
            if key == 'x':
                keys.restore()                            # the command has the terminal as the reader's shell gave it
                try:
                    ran = walk.run()
                finally:
                    keys.unbuffer()
                if isinstance(ran, str):
                    facts.say(walk.step(ran))
                else:
                    print('---')                          # what the command printed stands between the key's mark and this one, its own
                    facts.say(ran)
                    print('---')
                    facts.say(walk.step())
            else:
                facts.say(walk.step(walk.move(key)))
            sys.stdout.flush()
        print(f'-{left}-')
        facts.say(Left(walk.address()))
    finally:
        keys.restore()
    return GONE if astray else FAILED if walk.failed else 0


if __name__ == '__main__':
    sys.exit(main())
