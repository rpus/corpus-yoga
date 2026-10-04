#!/usr/bin/env python
"""
status.py - `corpus-yoga forge`'s standing report: the declared settings against the live
forge, the branches the forge knows, the tracking refs it has dropped, this checkout's gate
and upstream, read as rows on stdin from forge.sh, which holds each probe (#759):
`<section> <STATUS> <key> <detail> [<remedy>]`, tab-separated, the sections settings,
branches, refs, checkout. With --stage, the stage's units of the forge's captures follow -
the bare noun; without, the report alone - the merge's gate. Exit 1 on refuse-class drift.
Reads; writes nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/forge/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import corpus  # noqa: E402
import facts  # noqa: E402

REFUSING = {'settings': ('drift', 'unverified'), 'branches': ('unverified',), 'refs': ('unverified',),
            'checkout': ('wrong', 'unverified')}     # the states under which the merge refuses
TYPED = ('corpus-yoga ', 'git ', 'gh ')              # how a remedy the reader types begins


@dataclass
class Row:
    """One probe's answer: what it is about, what it found, its state, and the remedy where one stands."""
    key: str
    detail: str
    state: str
    remedy: str = ''

    def facts(self) -> dict:
        remedy = None if not self.remedy else facts.Command(self.remedy) if self.remedy.startswith(TYPED) else facts.Act(self.remedy)
        return {self.key: self.detail, 'state': self.state, 'remedy': remedy}


@dataclass
class Settings:
    declared: str
    live: str
    rows: list[Row]


@dataclass
class Status:
    forge_settings: Settings
    branches: list[Row] | None
    branches_remedy: facts.Command | None
    refs: list[Row] | None = facts.named('remote-tracking refs', default=None)
    refs_remedy: facts.Command | None = facts.named('remote-tracking refs remedy', default=None)
    checkout: list[Row] | None = facts.named('this checkout', default=None)
    staged: dict[str, list[corpus.StagedUnit]] | None = None
    stage: str | None = None
    forge: str = ''               # the verdict


def main() -> int:
    by_section: dict[str, list[Row]] = {}
    for line in sys.stdin.read().splitlines():
        cells = line.split('\t')
        if len(cells) < 4 or not cells[1]:
            continue
        by_section.setdefault(cells[0], []).append(Row(cells[2], cells[3], cells[1].lower(), cells[4] if len(cells) > 4 else ''))
    refused = any(row.state in REFUSING[section] for section, rows in by_section.items() for row in rows if section in REFUSING)
    branches, refs = by_section.get('branches'), by_section.get('refs')
    out = Status(
        Settings('src/main/cli/forge/forge.csv', "this checkout's remote", by_section.get('settings', [])),
        branches,
        facts.Command('corpus-yoga forge prune', 'removes each deletable branch')
        if branches and any(row.state in ('deletable', 'server_deletable') for row in branches) else None,
        refs, facts.Command('corpus-yoga forge prune') if refs and any(row.state == 'stale' for row in refs) else None,
        by_section.get('checkout'),
        forge='refuse-class drift - corpus-yoga forge merge refuses while it stands' if refused else 'ready - no refuse-class drift')
    if '--stage' in sys.argv[1:]:
        report = corpus.report_facts('forge')
        out.staged, out.stage = report.staged, report.stage
    facts.say(out)
    return 1 if refused else 0


if __name__ == '__main__':
    sys.exit(main())
