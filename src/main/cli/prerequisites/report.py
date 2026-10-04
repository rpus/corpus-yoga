#!/usr/bin/env python
"""
report.py - `corpus-yoga prerequisites`' report: the rows prerequisites.sh collects as its
checks run - `<section> <kind> <text> [<command> <what it does>]...`, tab-separated, in the
file named - typed and said as
one shape (#759). A row's commands are columns of their own, `<command> <what it does>` in
pairs after the text, and a row that carries any is keyed by what stands with its commands
beneath (#763, #765). Runs under the venv's python, or under python3 before the venv is
minted.

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

@dataclass
class Section:
    """One section of the report, its rows by kind (#763, #765). A row that stands with no
    command to act on it is a bare statement under its kind - ok, note, todo. A row the
    reader acts on is keyed by what stands, the commands that act on it beneath, each with
    what it does; one that is required and absent stands under `missing`."""
    ok: list[str]
    note: list[str]
    todo: list[str]
    acts: dict[str, dict[str, str]]       # what stands, then each command with what it does
    missing: dict[str, dict[str, str]]

    def facts(self) -> dict:
        return {'ok': self.ok or None, 'note': self.note or None, 'todo': self.todo or None,
                **self.acts, 'missing': self.missing or None}


@dataclass
class Report:
    stamp: str
    sections: dict[str, Section]
    verdict: str

    def facts(self) -> dict:
        return {'report': self.stamp, **self.sections, 'prerequisites': self.verdict}


def main() -> int:
    rows_file, verdict, stamp = sys.argv[1:4]
    sections: dict[str, Section] = {}
    for line in Path(rows_file).read_text().splitlines():
        if not line.strip():
            continue
        name, kind, text, *rest = line.split('\t')
        section = sections.setdefault(name, Section([], [], [], {}, {}))
        commands = {rest[i]: rest[i + 1] if i + 1 < len(rest) else '' for i in range(0, len(rest), 2) if rest[i]}
        if not commands:
            {'ok': section.ok, 'note': section.note}.get(kind, section.todo).append(text)
        elif kind == 'missing':
            section.missing[text] = commands
        else:
            section.acts[text] = commands
    facts.say(Report(stamp, sections, verdict))
    return 0


if __name__ == '__main__':
    sys.exit(main())
