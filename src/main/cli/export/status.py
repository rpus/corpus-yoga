"""
status.py - bare `corpus-yoga export`: the exports held and staged, each by its manifest within it,
then the stage's units of the export's captures, as one shape (issues/759). Reads; writes nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path
import corpus
import facts
import tier  # the repository root, which corpus-yoga hands every run (issues/1173)

REPO = tier.REPO


@dataclass
class Exports:
    """What an export is, then the ones held and the ones staged."""
    form: str = facts.named('an export <X>', default=facts.phrase("data-<X>/, its capture's manifest.json within it, staged and held alike"))
    held: dict[str, corpus.Deposit] | None = None
    staged: dict[str, corpus.Deposit] | None = None


@dataclass
class Status:
    export: Exports | str
    staged: dict[str, corpus.Staged]


def main() -> int:
    deposits = corpus.deposits_facts('export')
    report = corpus.report_facts('export')
    if not deposits.held and not deposits.staged:
        facts.say_standing(Status(facts.phrase('nothing held or staged'), report.staged))
        return 0
    facts.say_standing(Status(Exports(held=deposits.held, staged=deposits.staged), report.staged))
    return 0


if __name__ == '__main__':
    sys.exit(main())
