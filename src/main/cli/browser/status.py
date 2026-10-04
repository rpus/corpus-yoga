#!/usr/bin/env python
"""
status.py - bare `corpus-yoga browser`: the capture audit's offline pass, then the stage's
units of the browser's captures, as one shape (#759). Reads; writes nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/browser/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'pipeline' / 'chat-capture'))   # audit.py - the capture audit
import tier  # noqa: E402 - the tiers, one home (#702)
import corpus  # noqa: E402
import facts  # noqa: E402
import audit as capture_audit  # noqa: E402
from library import migration_note  # noqa: E402 - on the path audit.py inserts: the artifact library's stated move (#421)


@dataclass
class Status(capture_audit.Audit):
    """The audit's standing, then the staged units the browser captured and the stage's verdict."""
    staged: dict[str, dict[str, str]] | None = None
    stage: str = ''


def main() -> int:
    migration_note()
    shape, found = capture_audit.audit(tier.DATA / 'input', tier.DATA / 'output' / 'markdown' / 'claude' / 'chat' / 'conversations')
    report = corpus.report_facts('browser')
    facts.say(Status(shape.claude, shape.gemini, shape.claude_live, shape.gemini_live, report.staged, report.stage))
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
