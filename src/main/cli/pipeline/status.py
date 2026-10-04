#!/usr/bin/env python
"""
status.py - bare `corpus-yoga pipeline`: each pipeline with its phases, read as rows on stdin
from pipeline.sh, which holds what a phase is (`pipeline <name> <phases>`, tab-separated),
then the stage's every unit, as one shape (#759). Reads; writes nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/pipeline/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import corpus  # noqa: E402
import facts  # noqa: E402


@dataclass
class Pipelines:
    phases: dict[str, str]        # each pipeline's phases, in the order they run
    processing_only: str = 'acquisition is corpus-yoga browser, agent or indexing capture'
    steps: facts.Command = facts.Command('corpus-yoga pipeline run --plan')
    input_state: facts.Command = facts.Command('corpus-yoga prerequisites')

    def facts(self) -> dict:
        return {**self.phases, 'processing only': self.processing_only, 'steps': self.steps, 'input state': self.input_state}


@dataclass
class Status:
    pipelines: Pipelines
    staged: dict[str, list[corpus.StagedUnit]] | None
    stage: str


def main() -> int:
    phases = {name: said for kind, name, said in (row.split('\t') for row in sys.stdin.read().splitlines() if row.count('\t') == 2)
              if kind == 'pipeline'}
    report = corpus.report_facts(None)
    facts.say(Status(Pipelines(phases), report.staged, report.stage))
    return 0


if __name__ == '__main__':
    sys.exit(main())
