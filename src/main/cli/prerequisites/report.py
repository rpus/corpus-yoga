#!/usr/bin/env python
"""
report.py - `corpus-yoga prerequisites`' report: the rows prerequisites.sh collects as its
checks run - `<section> <kind> <subject> <what stands> [<command> <what it does>]...`,
tab-separated, in the file named - typed and said as
one shape (#759). A row is keyed by what it is about (#771); its commands are columns of
their own, `<command> <what it does>` in pairs, and stand beneath it (#763, #765). Runs
under the venv's python, or under python3 before the venv is minted.

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
class Report:
    """The report: each section its subjects, each subject what stands of it - a value where
    that is all, and where the reader can act, `stands` (or `missing`, where the thing is
    required and absent) with the commands that act on it beneath, each with what it does
    (#763, #771). A subject `a / b` stands beneath `a`."""
    stamp: str
    sections: dict[str, dict]
    verdict: str

    def facts(self) -> dict:
        return {'report': self.stamp, **self.sections, 'prerequisites': self.verdict}


def main() -> int:
    rows_file, verdict, stamp = sys.argv[1:4]
    sections: dict[str, dict] = {}
    for line in Path(rows_file).read_text().splitlines():
        if not line.strip():
            continue
        name, kind, subject, stands, *rest = line.split('\t')
        commands = {rest[i]: rest[i + 1] if i + 1 < len(rest) else '' for i in range(0, len(rest), 2) if rest[i]}
        at = sections.setdefault(name, {})
        *above, last = [part.strip() for part in subject.split(' / ')]
        for part in above:
            beneath = at.setdefault(part, {})
            if not isinstance(beneath, dict):         # a subject that stands and also holds others: its own standing moves beneath it
                beneath = at[part] = {'stands': beneath}
            at = beneath
        while last in at:                             # two rows of one subject: both are said
            last += ' (again)'
        at[last] = {('missing' if kind == 'missing' else 'stands'): stands, **commands} if commands else stands
    facts.say(Report(stamp, sections, verdict))
    return 0


if __name__ == '__main__':
    sys.exit(main())
