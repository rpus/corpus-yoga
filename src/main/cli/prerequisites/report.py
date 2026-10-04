#!/usr/bin/env python
"""
report.py - `corpus-yoga prerequisites`' report: the rows prerequisites.sh collects as its
checks run - `<section> <kind> <text> [<command> <what it does>]...`, tab-separated, in the
file named - typed and said as
one shape (#759). A row's commands are columns of their own, `<command> <what it does>` in
pairs after the text, and a row that carries any is keyed by them (#763). Runs under the
venv's python, or under python3 before the venv is minted.

usage: report.py <rows-file> <verdict> <stamp>
"""
from __future__ import annotations
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/prerequisites/report.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import facts  # noqa: E402

STANDS = {'todo': 'for', 'missing': 'missing'}   # under which key a row that carries commands says what stands


@dataclass
class Item:
    """One row of the report. A row that asks the reader to act is keyed by the commands
    that act on it, each with what it does, and says what stands beneath them (#763); any
    other is what stands, under its kind - ok, note, about, or a todo no command acts on."""
    kind: str
    text: str
    commands: list[facts.Command]

    def facts(self) -> dict:
        if not self.commands:
            return {self.kind: self.text}
        return {**{command.line: command.does for command in self.commands}, STANDS.get(self.kind, self.kind): self.text}


@dataclass
class Report:
    stamp: str
    sections: dict[str, list[Item]]
    verdict: str

    def facts(self) -> dict:
        return {'report': self.stamp, **self.sections, 'prerequisites': self.verdict}


def main() -> int:
    rows_file, verdict, stamp = sys.argv[1:4]
    sections: dict[str, list[Item]] = {}
    for line in Path(rows_file).read_text().splitlines():
        if not line.strip():
            continue
        section, kind, text, *rest = line.split('\t')
        commands = [facts.Command(rest[i], rest[i + 1] if i + 1 < len(rest) else '') for i in range(0, len(rest), 2) if rest[i]]
        sections.setdefault(section, []).append(Item(kind, text, commands))
    facts.say(Report(stamp, sections, verdict))
    return 0


if __name__ == '__main__':
    sys.exit(main())
