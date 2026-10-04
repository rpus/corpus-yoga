#!/usr/bin/env python
"""
report.py - `corpus-yoga prerequisites`' report: the rows prerequisites.sh collects as its
checks run - `<section> <kind> <text>`, tab-separated, in the file named - typed and said as
one shape (#759). A row's embedded remedy marker becomes its remedy, a Command. Runs under
the venv's python, or under python3 before the venv is minted.

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
import re  # noqa: E402
import facts  # noqa: E402

MARKER = re.compile(r'\s*[-\u2014]?\s*(\u2192 run:|install via:|reinstall:|replace:|refresh:)\s*')


@dataclass
class Item:
    """One row of the report: what stands, under its kind - ok, note, todo or missing."""
    kind: str
    text: str
    remedy: facts.Command | None = None

    def facts(self) -> dict:
        return {self.kind: self.text, 'remedy': self.remedy}


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
        section, kind, text = line.split('\t', 2)
        found = MARKER.search(text)
        item = Item(kind, text)
        if found:
            item = Item(kind, text[:found.start()].rstrip(' -\u2014'), facts.Command(text[found.end():].strip()))
        sections.setdefault(section, []).append(item)
    facts.say(Report(stamp, sections, verdict))
    return 0


if __name__ == '__main__':
    sys.exit(main())
