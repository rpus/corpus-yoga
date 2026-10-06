#!/usr/bin/env python
"""
status.py - bare `corpus-yoga export`: the exports held and staged, each paired or unpaired,
then the stage's units of the export's captures, as one shape (#759). Reads; writes nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/export/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import corpus  # noqa: E402
import facts  # noqa: E402


@dataclass
class Exports:
    """What an export is, then the ones held and the ones staged."""
    form: str = facts.named('a staged export <X>', default="data-<X>/ with manifest-<X>.json, its capture's record")
    shared: str = facts.named('shared storage holds', default='data-<X>/')
    held: dict[str, corpus.Paired] | None = None
    staged: dict[str, corpus.Paired] | None = None


@dataclass
class Status:
    export: Exports | str
    staged: dict[str, corpus.Staged]
    remedy: facts.Act | dict[str, str] | None


def main() -> int:
    pairs = corpus.pairs_facts('export')
    report = corpus.report_facts('export')
    if not pairs.held and not pairs.staged:
        facts.say(Status('nothing held or staged', report.staged, facts.Act(
            'request an export at https://claude.ai/settings/data-privacy-controls, then '
            'corpus-yoga export capture --manifest <the downloaded manifest>')))
        return 0
    facts.say(Status(Exports(held=pairs.held, staged=pairs.staged), report.staged, report.remedy))
    return 0


if __name__ == '__main__':
    sys.exit(main())
