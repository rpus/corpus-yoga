#!/usr/bin/env python
"""
walkthrough.py - `corpus-yoga walkthrough`: the room's state as one tree, walked by the
reader (#766). The tree's first level is the commands, the machine report first. Under
each stand its status, where it has one - what its bare status prints, loaded when the
walk first descends into it: the lines are the data (#753), so the walk has no second
interface to any noun - and its help: its declaration, as it states it (#770). So help is
read as the state is, with the same keys, and what does not vary with the room is read
beside what does. Four keys move it, one row of the keyboard, and a fifth leaves:

  n  next   the next sibling at this depth - pressed from the top, the outline
  m  more   into the node the walk stands on: its first child, or its value where it holds one
  b  back   over the last move
  x  run    the command the walk stands on, in the foreground; the state is read again after
  q  quit

A key is the head of what it holds, and a step says the head alone: the key, its place,
and the size and shape of what m would give - so many keys, so many bare values, a value
of so many words - never the thing itself, so the reader chooses to descend knowing what
follows and no step scrolls. Every spot has an address, its JSON pointer (RFC 6901) from the top of the tree - a `/`
before each key, `~1` for a slash within one and `~0` for a tilde, a bare value by its
place in its list (#775). A step says the spot's pointer; `corpus-yoga walkthrough
<pointer>` starts there, reading what the pointer passes through; and on leaving the walk
says the command that continues from where it left.

A key is read from the terminal as it is pressed, or as a
line on stdin, so a model or a test walks as a reader does. Each step is said as facts,
one YAML document per step, and the mark between two steps is the key that made the
second - `-n-`, `-m-`, `-b-`, `-x-`, `-q-` - so the transcript is its own history. The
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
KEYS = 'n next, m more, b back, x run, q quit'
UNREAD = object()                                     # a noun whose status the walk has not yet read


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


def status(noun: str):
    """A noun's facts: what its bare status prints, loaded - or, in words, why it cannot be read."""
    if not venv() and noun != REPORT:
        return f'unread - the venv is not minted; {REPORT} says how'
    command = [str(REPO / 'corpus-yoga'), noun] if venv() else [REPORT_SCRIPT]
    asked = subprocess.run(command, capture_output=True, text=True, cwd=REPO)
    try:
        loaded = facts.load(asked.stdout)
    except ValueError as error:
        return f'unreadable - {error}'
    if isinstance(loaded, dict):
        loaded.pop('usage', None)                     # the CLI's tail, not the noun's state
    return loaded if loaded else f'nothing said (exit {asked.returncode})'


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
    """Where the walk stands: the node, its place among its siblings, and what it holds."""
    at: str                                           # the spot's address: its JSON pointer from the top
    key: str
    place: str                                        # its position among its siblings
    holds: str | None = None                          # the size and shape of what m would give, never the thing
    value: object = None                              # the value, once m has asked for it
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
        return {'walkthrough': f'left at {self.at}', f'corpus-yoga walkthrough {shlex.quote(self.at)}': 'continues from there'}


@dataclass
class Walk:
    """The tree, and the walk's place in it: the path of keys from the top."""
    tree: dict = field(default_factory=dict)
    path: list[str] = field(default_factory=list)
    history: list[tuple[list[str], bool]] = field(default_factory=list)
    shown: bool = False                               # whether m has asked for the value the walk stands on

    def __post_init__(self):
        self.tree = room()
        self.path = [next(iter(self.tree))]

    def node(self, path: list[str], read: bool = False):
        """What stands at the path. A status is read where the path passes through it, or
        ends on it and `read` asks; until then it stands unread."""
        at = self.tree
        for depth, key in enumerate(path):
            if isinstance(at, list):
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
        """Stand on the spot the pointer names, reading what it passes through; where no
        such spot stands, on the nearest that does, with the note that says so."""
        try:
            tokens = tokens_of(pointer)
        except ValueError as error:
            return str(error)
        path: list[str] = []
        for token in tokens:
            here = self.node(path, read=True) if path else self.tree
            if isinstance(here, dict) and token in here:
                path.append(token)
            elif isinstance(here, list) and token.isdigit() and int(token) < len(here):
                path.append(str(here[int(token)]))
            else:
                break
        if path:
            self.path = path
        return None if len(path) == len(tokens) else f'no spot stands at {pointer} - the nearest is {self.address()}'

    def siblings(self) -> list[str]:
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
        here = self.node(self.path)
        return here is not UNREAD and not isinstance(here, (dict, list)) and isinstance(self.node(self.path[:-1]), dict)

    def move(self, key: str) -> str | None:
        """Take one key; the note where it moved nothing."""
        if key == 'n':
            around = self.siblings()
            place = around.index(self.path[-1])
            if place + 1 == len(around):
                return f'the last of {len(around)} - b goes back'
            self.history.append((list(self.path), self.shown))
            self.path[-1], self.shown = around[place + 1], False
        elif key == 'm':
            beneath = self.children()
            if beneath:
                self.history.append((list(self.path), self.shown))
                self.path.append(beneath[0])
                self.shown = False
            elif self.leaf() and not self.shown:
                self.history.append((list(self.path), self.shown))
                self.shown = True
            else:
                return 'nothing more - n goes on, b goes back'
        elif key == 'b':
            if not self.history:
                return 'the walk began here'
            self.path, self.shown = self.history.pop()
        else:
            return f'{key!r} is no key - {KEYS}'
        return None

    def step(self, note: str | None = None, keys: bool = False) -> Step:
        around = self.siblings()
        key = self.path[-1]
        here = self.node(self.path)
        if here is UNREAD:
            holds = 'unread - m reads it'
        elif isinstance(here, dict):
            holds = f'{len(here)} key' + ('' if len(here) == 1 else 's')
        elif isinstance(here, list):
            holds = f'{len(here)} bare value' + ('' if len(here) == 1 else 's')
        elif self.leaf():
            words = len(str(here).split())
            holds = f'a value, {words} word' + ('' if words == 1 else 's')
        else:
            holds = None                              # a bare value: the key is all of it
        command = command_of(key)
        return Step(self.address(), key, f'{around.index(key) + 1} of {len(around)}',
                    holds=holds, value=here if self.shown and here is not UNREAD else None,
                    runs='x - ' + ' '.join(key.split()) if command else None,
                    note=note, keys=KEYS if keys else None)

    def run(self) -> Ran | str:
        """Run the command the walk stands on, in the foreground, then forget what was read."""
        command = command_of(self.path[-1])
        if command is None:
            return 'no command stands here - x runs a key that is a corpus-yoga command' + (
                '; this one holds a placeholder, and is the reader\'s to type' if '<' in self.path[-1] else '')
        sys.stdout.flush()
        done = subprocess.run(command, cwd=REPO)
        self.tree = room()
        self.history.clear()
        self.shown = False
        while len(self.path) > 1 and not self._stands():
            self.path.pop()                           # the state moved: stand on what is left of the path
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
    pointer = next((argument for argument in sys.argv[1:] if not argument.startswith('-')), None)
    astray = walk.seek(pointer) if pointer is not None else None
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
    return 0


if __name__ == '__main__':
    sys.exit(main())
