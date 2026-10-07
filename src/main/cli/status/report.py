#!/usr/bin/env python
"""
report.py - `corpus-yoga status`' report: the rows status.sh collects as its
checks run - `<section> <kind> <subject> <what stands> [<command> <what it does>]...`,
tab-separated, in the file named - typed and said as one shape (#759). A row is keyed by
what it is about (#771); its commands are columns of their own, `<command> <what it does>`
in pairs, and stand under `remedy` beside it (#763, #777). A row `<section> graft <noun>
<pointer>` is what that noun's own status says at that spot, loaded as the data it is
(#777): whole in the full report, and otherwise what holds a remedy. Runs under the venv's
python, or under python3 before the venv is minted, where no noun can be asked.

usage: report.py report <rows-file> <stamp> <show-all: 0|1>
       report.py remedies <rows-file> ...      # each remedy the report holds: command, what it does, where
"""
from __future__ import annotations
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/status/report.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import facts  # noqa: E402


@dataclass
class Report:
    """The report: each section its subjects, each subject what stands of it (#763, #771). A
    subject `a / b` stands beneath `a`, so its last part names the property the value is of,
    or is the thing itself by its address; the commands that act on a row stand under
    `remedy` beside its last part, each with what it does. No key names a kind."""
    stamp: str
    sections: dict[str, dict]

    def facts(self) -> dict:
        return {'report': self.stamp, **self.sections}


def needing(node):
    """What of a noun's facts needs acting on: each mapping that holds a remedy, whole, under
    the keys that lead to it; None where nothing does."""
    if not isinstance(node, dict):
        return None
    if 'remedy' in node:
        return node
    kept = {key: found for key, value in node.items() if (found := needing(value)) is not None}
    return kept or None


_said: dict[str, object] = {}     # each noun's status, read once a report, however many spots are grafted from it


def read_at_once(nouns: list[str]) -> None:
    """Read every grafted noun's status together, so the report takes the time of the
    slowest and not their sum (#811): each is a process of its own, and none reads another."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, len(nouns))) as pool:
        for noun in nouns:
            pool.submit(said_by, noun)


def said_by(noun: str):
    """What the noun's bare status says, loaded; or, in words, why it could not be read."""
    if noun not in _said:
        asked = subprocess.run([str(REPO / 'corpus-yoga'), noun], capture_output=True, text=True, cwd=REPO)
        try:
            at = facts.load(asked.stdout)
        except ValueError as error:
            at = f'corpus-yoga {noun} is unreadable - {error}'
        if isinstance(at, dict):
            at.pop('usage', None)
        _said[noun] = at
    return _said[noun]


def grafted(noun: str, pointer: str, whole: bool):
    """What the noun's own status says at the pointer: its facts, loaded. None where the
    short report has nothing of it to show."""
    venv = Path(os.environ.get('CORPUS_YOGA_VENV', Path.home() / 'venvs' / 'general')) / 'bin' / 'python'
    if not venv.is_file():
        return 'unread - the venv is not minted' if whole else None
    at = said_by(noun)
    if isinstance(at, str):
        return at
    for token in ([t.replace('~1', '/').replace('~0', '~') for t in pointer[1:].split('/')] if pointer else []):
        if not isinstance(at, dict) or token not in at:
            return f'corpus-yoga {noun} says nothing at {pointer}' if whole else None   # a spot the noun has no occasion for: nothing to remedy
        at = at[token]
    return at if whole else needing(at)


def remedies(node, where: str = '') -> list[tuple[str, str, str]]:
    """Each remedy the report holds: its command, what it does, and where it stands."""
    if not isinstance(node, dict):
        return []
    out = [(command, does, where) for command, does in node['remedy'].items()] if isinstance(node.get('remedy'), dict) else []
    for key, value in node.items():
        if key != 'remedy':
            out += remedies(value, f'{where} / {key}' if where else str(key))
    return out


def main() -> int:
    mode, rows_file, stamp, show_all = (sys.argv[1:5] + ['', '', ''])[:4]
    whole = show_all == '1' or mode == 'remedies'       # sync reads every remedy, whatever the report shows
    sections: dict[str, dict] = {}
    rows = [line.split('\t') for line in Path(rows_file).read_text().splitlines() if line.strip()]
    venv = Path(os.environ.get('CORPUS_YOGA_VENV', Path.home() / 'venvs' / 'general')) / 'bin' / 'python'
    if venv.is_file():
        read_at_once(sorted({row[2] for row in rows if row[1] == 'graft'}))
    for name, kind, subject, stands, *rest in rows:
        if kind == 'graft':
            # the section is the command (#812); beneath it, what stands at the pointer, under
            # the pointer's last key - or merged whole where the pointer names the noun itself
            said = grafted(subject, stands, whole)
            if said is None:
                continue
            last = stands.rsplit('/', 1)[-1].replace('~1', '/').replace('~0', '~')
            section = sections.setdefault(name, {})
            if isinstance(said, dict) and (not stands or last == subject):
                section.update(said)
            else:
                section[last if last and last != subject else subject] = said
            continue
        at = sections.setdefault(name, {})
        *above, last = [part.strip() for part in subject.split(' / ')]
        for part in above:
            beneath = at.setdefault(part, {})
            if not isinstance(beneath, dict):         # a subject that held one value and now holds others: the value keeps its place by name
                beneath = at[part] = {part: beneath}
            at = beneath
        while last in at:                             # two rows of one subject: both are said
            last += ' (again)'
        at[last] = stands
        commands = {rest[i]: rest[i + 1] if i + 1 < len(rest) else '' for i in range(0, len(rest), 2) if rest[i]}
        if commands:
            at.setdefault('remedy', {}).update(commands)
    if mode == 'remedies':
        for command, does, where in remedies(sections):
            print(f'{command}\t{does}\t{where}')
        return 0
    facts.say(Report(stamp, sections))
    return 0


if __name__ == '__main__':
    sys.exit(main())
