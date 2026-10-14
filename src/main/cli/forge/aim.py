#!/usr/bin/env python
"""aim.py - the one grammar of a PR's aim: the relation between a PR and the issues it
aims to complete, as the body carries it (#884).

An aim is one line, `- aims to complete #N - <title>`, one issue per line, and nothing
else in a body may say the phrase outside backticks: corpus-yoga forge raise writes the
lines, corpus-yoga forge merge reads the aimed set from them and refuses any other
spelling, and the flip rewrites each to `- closes #N - <title>`, the one word GitHub
binds its closing to, so that the set the merge flips and the set the squash closes
are one. Mentions of the phrase wear backticks, as the PR template rules, and are
stripped before reading.

Faces:
    aim.py aimed  <body   prints each aimed issue's number, one per line; exit 1 naming
                          a line that says the phrase otherwise
    aim.py flip   <body   prints the body with each aim line flipped to closes
"""
import re
import sys
from pathlib import Path

SELF = 'src/main/cli/forge/aim.py'
_file = Path(__file__).resolve()
assert [p for p in _file.parents if p / SELF == _file], f'{_file} is not at its declared address {SELF}'

PHRASE = 'aims to complete'
CLOSES = 'closes'
_AIM = re.compile(r'^- aims to complete #(\d+) - ([^#]*)$')
_CODE = re.compile(r'`[^`]*`')


def line(number: int, title: str) -> str:
    """The aim line for one issue: its number and its title, which holds no `#`."""
    if '#' in title:
        raise ValueError(f'#{number}: a title holding # cannot be an aim line: {title}')
    return f'- {PHRASE} #{number} - {title}'


def aimed(body: str) -> list[int]:
    """The issues the body aims to complete, in order, each once; a line that says the
    phrase and is not one aim line is refused by name."""
    numbers: list[int] = []
    for raw in body.splitlines():
        if PHRASE not in _CODE.sub('', raw):
            continue
        match = _AIM.match(raw.rstrip())
        if not match:
            raise ValueError(f'a line says the phrase otherwise than one aim per line: {raw.strip()[:120]}')
        number = int(match.group(1))
        if number not in numbers:
            numbers.append(number)
    return numbers


def flipped(body: str) -> str:
    """The body armed: each aim line's phrase becomes closes, nothing else rewritten."""
    return '\n'.join(re.sub(r'^- aims to complete #', f'- {CLOSES} #', raw) for raw in body.split('\n'))


def main(argv: list[str]) -> int:
    body = sys.stdin.read()
    if argv == ['aimed']:
        try:
            sys.stdout.write(''.join(f'{n}\n' for n in aimed(body)))
        except ValueError as why:
            print(why, file=sys.stderr)
            return 1
        return 0
    if argv == ['flip']:
        aimed(body)                                   # a body the merge cannot read is not flipped
        sys.stdout.write(flipped(body))
        return 0
    print(f'usage: {SELF} aimed|flip <body', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
