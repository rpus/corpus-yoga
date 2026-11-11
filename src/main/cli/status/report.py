#!/usr/bin/env python
"""
report.py - `corpus-yoga status`' report: the rows status.sh collects as its
checks run - `<section> <kind> <subject> <what stands> [<command> <what it does>]...`,
tab-separated, in the file named - typed and said as one shape (issues/759). A row is keyed by
what it is about (issues/771) and says the fact alone; its commands are columns of their own,
`<command> <what it does>` in pairs, each an act said under now: (issues/1050). A row `<section>
graft <noun> <pointer>` is what that noun's own status says at that spot, loaded as the data it is
(issues/777): whole in the full report, and in the short one only with `standing` as a fifth column
(issues/824) - the spot's facts as they stand - since every other spot's acts reach the report
through now:. The report ends on now:, the room's standing folded once from every noun's own
(src/main/standing.py, issues/949) with the acts the rows name - every act under MAY or MUST, as
its verb declares. Runs under the venv's python, or under python3 before the venv is minted,
where no noun can be asked.

usage: report.py report <rows-file> <show-all: 0|1>
       report.py must <rows-file> ...          # each MUST act: command, what it does, where
"""
from __future__ import annotations
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import facts
import spell
import standing

SELF = 'src/main/cli/status/report.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]


@dataclass
class Report:
    """The report: each section its subjects, each subject what stands of it (issues/763, issues/771). A
    subject `a / b` stands beneath `a`, so its last part names the property the value is of,
    or is the thing itself by its address. No key names a kind, and no act stands in a section:
    every act is now:'s (issues/1050)."""
    sections: Mapping[str, object]
    now: dict | str = facts.phrase('unread - the venv is not minted')   # the room's standing, last (issues/949)

    def facts(self) -> dict:
        return {**{name: self.sections[name] for name in sorted(self.sections)}, 'now': self.now}   # one order, a reader's: alphabetical, the standing last


def grafted(noun: str, pointer: str, whole: bool, as_standing: bool = False):
    """What the noun's own status says at the pointer: its facts, loaded, its now: left to the
    room's, which folds every noun's (issues/1050). None where the short report has nothing of it
    to show: every spot but one grafted as standing (issues/824), whose facts show as they stand -
    a mapping or a list, never the sentence that says the spot is empty."""
    if not whole and not as_standing:
        return None
    venv = Path(os.environ.get('CORPUS_YOGA_VENV', Path.home() / 'venvs' / 'general')) / 'bin' / 'python'
    if not venv.is_file():
        return facts.phrase('unread - the venv is not minted') if whole else None
    at = standing.said_by(noun)
    if isinstance(at, str):
        return at
    if isinstance(at, dict):
        at = {key: value for key, value in at.items() if key != 'now'}
    for token in ([t.replace('~1', '/').replace('~0', '~') for t in pointer[1:].split('/')] if pointer else []):
        if not isinstance(at, dict) or token not in at:
            return facts.phrase('corpus-yoga {noun} says nothing at {pointer}', noun=noun, pointer=pointer) if whole else None   # a spot the noun has no occasion for
        at = at[token]
    if whole:
        return at
    return at if isinstance(at, (dict, list)) and at else None


def _is_act(command: str) -> bool:
    """Whether the command is a corpus-yoga act whose verb declares what it would do."""
    try:
        facts.would_of(command)
    except (StopIteration, IndexError, OSError, KeyError, ValueError):
        return False
    return True


def must(now) -> list[tuple[str, str, str]]:
    """Each MUST act of a now:, as status satisfy is handed it: its command, what it does, and
    what it acts on."""
    out: list[tuple[str, str, str]] = []
    for command, does in (now.get('MUST', {}) if isinstance(now, dict) else {}).items():
        for would, acts_on in does.items():
            if would == facts.REPORTS:
                continue   # a fault owed by hand: said, never run
            out.append((command, would, ', '.join(map(str, acts_on)) if isinstance(acts_on, dict) else str(acts_on)))
    return out


def main() -> int:
    mode, rows_file, show_all = (sys.argv[1:4] + ['', ''])[:3]
    whole = show_all == '1'
    sections: dict[str, dict] = {}
    acts: list[facts.Would] = []
    typed: list[tuple[str, str, str]] = []   # each command a row names, as the row names it: what satisfy runs of the rows
    rows = [line.split('\t') for line in Path(rows_file).read_text().splitlines() if line.strip()]
    venv = Path(os.environ.get('CORPUS_YOGA_VENV', Path.home() / 'venvs' / 'general')) / 'bin' / 'python'
    if venv.is_file():
        standing.read_at_once(sorted({row[2] for row in rows if row[1] == 'graft'} | set(standing.NOUNS)))   # the grafted and the folded, one batch
    for name, kind, subject, stands, *rest in rows:
        if kind == 'graft':
            # the section is the command (issues/812); beneath it, what stands at the pointer, under
            # the pointer's last key - or merged whole where the pointer names the noun itself
            said = grafted(subject, stands, whole, rest[:1] == ['standing'])
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
        thing = last
        while last in at:                             # two rows of one subject: both are said
            last += ' (again)'
        at[last] = stands
        for i in range(0, len(rest), 2):
            command, does = rest[i], rest[i + 1] if i + 1 < len(rest) else ''
            if not command:
                continue
            if not _is_act(command) or facts.Would(command, {}).modality == 'MUST':   # a row's act is satisfy's only as its verb declares
                typed.append((command, does, f'{name} / {subject}'))
            # a corpus-yoga act is said in its declared words, on what the row is about (issues/1028);
            # any other command is one status satisfy runs, and is said as its act (issues/1034)
            acts.append(facts.Would(command, {thing: 1}) if _is_act(command)
                        else facts.Would(spell.line('status', 'satisfy'), {above[0] if above else thing: 1}))
    own = facts.now_of(facts.Acts(tuple(acts)))
    if mode == 'must':
        # what satisfy runs: each command the rows name as typed, and every MUST act of the nouns
        for command, does, where in typed + (must(standing.room_now()) if venv.is_file() else []):
            print(f'{command}\t{does}\t{where}')
        return 0
    report = Report(sections)   # with no row to say, the report is its now: alone
    if venv.is_file():
        report.now = facts.ordered(facts.merge(standing.room_now(), own, once=True)) or facts.phrase('none - nothing to do')
    elif own:
        report.now = own
    facts.say(report)
    return 0


if __name__ == '__main__':
    sys.exit(main())
