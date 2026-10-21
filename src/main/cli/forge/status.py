#!/usr/bin/env python
"""
status.py - `corpus-yoga forge`'s standing report: the declared settings against the live
forge, the branches the forge knows, the tracking refs it has dropped, this checkout's gate
and upstream, read as rows on stdin from forge.sh, which holds each probe (issues/759):
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
TYPED = ('corpus-yoga ', 'git ', 'gh ', 'brew ')     # how a remedy the reader types begins; its does is the row's sixth cell


@dataclass
class Row:
    """One probe's answer, under what it is about (issues/779): the answer alone where the probe is
    satisfied, the answer under the state's word where it is not - one fact a line, never
    a sentence joining the two (issues/871) - and where a remedy stands, its `remedy` beside it (issues/777)."""
    answer: str
    state: str
    remedy: facts.Command | facts.Act | None = None

    def facts(self) -> dict | str:
        if self.state == 'ok' and self.remedy is None:
            return self.answer
        return {self.state: self.answer, **({'remedy': self.remedy} if self.remedy is not None else {})}


@dataclass
class Section:
    rows: dict[str, Row]          # by what each probe is about
    remedy: facts.Command | None = None

    def facts(self) -> dict:
        return {**self.rows, 'remedy': self.remedy}


@dataclass
class Settings(Section):
    """The merge settings: each as the forge has it where it agrees with src/main/cli/forge/forge.csv,
    its drift and remedy where it does not, or the one row saying why the forge was not read."""


@dataclass
class Status:
    forge_settings: Settings
    branches: Section | None
    refs: Section | None = facts.named('remote-tracking refs', default=None)
    checkout: Section | None = facts.named('this checkout', default=None)
    staged: dict[str, corpus.Staged] | None = None
    forge: str = ''               # the merge's gate, a fact of the room; a status ends on now: (issues/740)
    now: dict[str, dict[str, dict[str, int]]] | str | None = None   # by command, its verb, each thing it acts on: how many (issues/871, issues/947)


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
    opens: dict[str, str] = {}        # each open PR by its number: its head branch (issues/947)
    for line in sys.stdin.read().splitlines():
        cells = line.split('\t')
        if len(cells) < 4 or not cells[1]:
            continue
        section, state, said = cells[0], cells[1].lower(), cells[4] if len(cells) > 4 else ''
        if state == 'pr':
            opens[cells[2]] = cells[3]
            continue
        does = cells[5] if len(cells) > 5 else ''
        remedy = None if not said else facts.Command(said, does) if said.startswith(TYPED) else facts.Act(said)
        if section == 'settings' and state == 'drift':
            remedy = facts.Command('corpus-yoga forge sync', facts.phrase('would set it as declared'))   # the act; the status is its dry run (issues/881)
        by_section.setdefault(section, {})[cells[2]] = Row(cells[3], state, remedy)
    refused = any(row.state in REFUSING[section] for section, rows in by_section.items() if section in REFUSING
                  for row in rows.values())
    # the commit hook's state is the test noun's to say (issues/777, issues/778): the gate row is its saying
    hook = _test_status().commit_hook()
    by_section['checkout'] = {'pre-commit': Row(hook.installed.removeprefix('yes - '), 'ok' if hook.sound else 'wrong', hook.remedy),
                              **by_section.get('checkout', {})}
    branches, refs, checkout = by_section.get('branches'), by_section.get('refs'), by_section.get('checkout')
    # the standing (issues/871, issues/947): the cleaner over each branch and each tracking ref it
    # would remove, by name, and each open PR's merge over its head branch while no
    # refuse-class drift stands - the dry run is the status, and the room's one reading
    # folds this block; unread where the forge was not asked
    now: dict[str, dict[str, dict[str, int]]] = {}
    for name, row in (branches or {}).items():
        if row.state in ('deletable', 'server_deletable'):
            corpus.step(now, 'corpus-yoga forge clean', name)
    for name, row in (refs or {}).items():
        if row.state == 'stale':
            corpus.step(now, 'corpus-yoga forge clean', name)
    if not refused:
        for number, head in opens.items():
            corpus.step(now, f'corpus-yoga forge merge {number}', head)
    unread = any(row.state == 'unverified' for row in (branches or {}).values())
    out = Status(
        Settings(by_section.get('settings', {})),
        Section(branches) if branches else None,
        Section(refs) if refs else None,
        Section(checkout) if checkout else None,
        forge=facts.phrase('refuse-class drift - corpus-yoga forge merge refuses while it stands') if refused
        else facts.phrase('ready - no refuse-class drift'))
    if '--stage' in sys.argv[1:]:
        report = corpus.report_facts('forge')
        out.staged = report.staged
    out.now = now or facts.phrase('unread - the forge was not asked; branches says why' if unread else 'none - nothing to do')
    facts.say(out)
    return 1 if refused else 0


if __name__ == '__main__':
    sys.exit(main())
