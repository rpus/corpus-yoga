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
DOES = {('settings', 'drift'): 'sets it as declared',
        ('settings', 'moved'): 'names the repository as the forge answers for it',
        ('checkout', 'wrong'): 'puts it right'}      # what a row's remedy does, where the row gives the command alone


@dataclass
class Row:
    """One probe's answer, under what it is about (#779): the answer alone where the probe is
    satisfied, the state's word first where it is not, and where a remedy stands, the answer
    under that word with its `remedy` beside it (#777)."""
    answer: str
    state: str
    remedy: facts.Command | facts.Act | None = None

    def facts(self) -> dict | str:
        if self.remedy is None:
            return self.answer if self.state == 'ok' else f'{self.state} - {self.answer}'
        return {self.state: self.answer, 'remedy': self.remedy}


@dataclass
class Section:
    rows: dict[str, Row]          # by what each probe is about
    remedy: facts.Command | None = None

    def facts(self) -> dict:
        return {**self.rows, 'remedy': self.remedy}


@dataclass
class Settings(Section):
    declared: str = 'src/main/cli/forge/forge.csv'
    live: str = "this checkout's remote"

    def facts(self) -> dict:
        return {'declared': self.declared, 'live': self.live, **self.rows}


@dataclass
class Status:
    forge_settings: Settings
    branches: Section | None
    refs: Section | None = facts.named('remote-tracking refs', default=None)
    checkout: Section | None = facts.named('this checkout', default=None)
    staged: dict[str, corpus.Staged] | None = None
    forge: str = ''               # the verdict


def _test_status():
    """The test noun's status module, loaded by its address: the home of the hooks' state."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('test_status', REPO / 'src' / 'main' / 'cli' / 'test' / 'status.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules['test_status'] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    by_section: dict[str, dict[str, Row]] = {}
    for line in sys.stdin.read().splitlines():
        cells = line.split('\t')
        if len(cells) < 4 or not cells[1]:
            continue
        section, state, said = cells[0], cells[1].lower(), cells[4] if len(cells) > 4 else ''
        remedy = None if not said else facts.Command(said, DOES.get((section, state), 'then it is deletable')) \
            if said.startswith(TYPED) else facts.Act(said)
        by_section.setdefault(section, {})[cells[2]] = Row(cells[3], state, remedy)
    refused = any(row.state in REFUSING[section] for section, rows in by_section.items() if section in REFUSING
                  for row in rows.values())
    # the commit hook's state is the test noun's to say (#777, #778): the gate row is its saying
    hook = _test_status().commit_hook()
    by_section['checkout'] = {'pre-commit': Row(hook.installed.removeprefix('yes - '), 'ok' if hook.sound else 'wrong', hook.remedy),
                              **by_section.get('checkout', {})}
    branches, refs, checkout = by_section.get('branches'), by_section.get('refs'), by_section.get('checkout')
    out = Status(
        Settings(by_section.get('settings', {})),
        Section(branches, facts.Command('corpus-yoga forge prune', 'removes each deletable branch')
                if any(row.state in ('deletable', 'server_deletable') for row in branches.values()) else None) if branches else None,
        Section(refs, facts.Command('corpus-yoga forge prune', 'drops each stale ref')
                if any(row.state == 'stale' for row in refs.values()) else None) if refs else None,
        Section(checkout) if checkout else None,
        forge='refuse-class drift - corpus-yoga forge merge refuses while it stands' if refused else 'ready - no refuse-class drift')
    if '--stage' in sys.argv[1:]:
        report = corpus.report_facts('forge')
        out.staged = report.staged
    facts.say(out)
    return 1 if refused else 0


if __name__ == '__main__':
    sys.exit(main())
