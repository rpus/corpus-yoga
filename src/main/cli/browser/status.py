#!/usr/bin/env python
"""
status.py - bare `corpus-yoga browser`: the capture audit's offline pass, then each account as
last fetched against the captures (corpus-yoga browser fetch records it), then the stage's units
of the browser's captures, as one shape (issues/759). Reads; writes nothing, sends nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path
import tier  # the tiers, one home (issues/702)
import corpus
import facts
import audit as capture_audit
import account  # this file's sibling
from library import migration_note

SELF = 'src/main/cli/browser/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]


@dataclass
class Status(capture_audit.Audit):
    """The audit's standing, each account as last fetched against the captures, then the
    staged units the browser captured, each by its facts."""
    claude_account: account.Account | account.Unfetched | None = None
    gemini_account: account.Account | account.Unfetched | None = None
    staged: dict[str, corpus.Staged] | None = None


def main() -> int:
    migration_note()
    shape, found = capture_audit.audit(tier.DATA / 'input', tier.DATA / 'output' / 'markdown' / 'claude' / 'chat' / 'conversations')
    accounts = {provider: account.account(provider, account.RECORD / f'{provider}.json') for provider in ('claude', 'gemini')}
    report = corpus.report_facts('browser')
    facts.say_standing(Status(shape.claude, shape.gemini, accounts['claude'], accounts['gemini'], report.staged))
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
