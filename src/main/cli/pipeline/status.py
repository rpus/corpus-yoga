#!/usr/bin/env python
"""
status.py - bare `corpus-yoga pipeline`: each pipeline by its declaration and the steps its
plan names, read as rows on stdin from pipeline.sh (`pipeline <name> <prep step or ->`,
tab-separated), then the stage's every unit by its facts, as one shape (issues/759, issues/800).
Reads; writes nothing.
"""
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
import corpus
import facts
import frontier
import spell
import validation_audit  # the audit reads what a run is owed for (issues/1005)

SELF = 'src/main/cli/pipeline/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

PIPELINE_ROOT = REPO / 'src' / 'main'


@dataclass
class Pipeline:
    """A pipeline as its declaration (src/main/<name>/pipeline.json) says it, and
    the steps its own plan names, in order."""
    input: str
    providers: list[str] | None
    unit: str | dict[str, str] | None
    measure: str | dict[str, str] | None
    schemas: list[str]
    steps: list[str]
    remedy: facts.Would | None = None     # the run, for what it is owed one (issues/1005)


@dataclass
class Status:
    pipelines: dict[str, Pipeline]
    staged: dict[str, corpus.Staged]
    now: dict | str = facts.phrase('none - nothing to do')   # every act the body names, gathered (issues/1028)


def owed_runs() -> dict[str, facts.Would]:
    """The run each pipeline is owed, by its name, with what it would process by selection
    (issues/1005): the inputs with no output and those whose output was built from other
    bytes, read by the audit."""
    out: dict[str, facts.Would] = {}
    for name, declared in frontier.pipelines():
        owed = validation_audit.owed_by_selection(name, declared)
        if owed:
            out[name] = facts.Would(spell.line('pipeline', 'run', name), owed)
    return out


def steps_of(name: str, prep: str | None) -> list[str]:
    """The steps the pipeline's plan names (`run.sh --plan`, the one authority on their
    order), the prep step pipeline.sh runs before them first."""
    plan = subprocess.run([str(PIPELINE_ROOT / name / 'run.sh'), '--plan'], capture_output=True, text=True, cwd=REPO).stdout
    steps = [prep] if prep else []
    for line in plan.splitlines():
        if line.startswith('  ') and not line.rstrip().endswith(':'):
            words = line.split()
            word = ' '.join(words[:3]) if words[0] == 'corpus-yoga' else words[0]   # a step that is a corpus-yoga verb keeps its verb
            if word not in steps:
                steps.append(word)
    return steps


def one_or_each(by_provider: dict[str, str]):
    """A fact every provider shares, said once; otherwise each provider's."""
    return next(iter(by_provider.values())) if len(set(by_provider.values())) == 1 else by_provider


def pipeline(name: str, prep: str | None) -> Pipeline:
    declared = json.loads((PIPELINE_ROOT / name / 'pipeline.json').read_text())
    providers = declared.get('provider')
    if providers:
        unit = one_or_each({p: v['unit'] for p, v in providers.items()})
        measure = one_or_each({p: v['measure'] for p, v in providers.items()})
    else:
        unit, measure = declared.get('unit'), declared.get('measure')
    return Pipeline(declared['input'], list(providers) if providers else None, unit or None, measure or None,
                    declared['schemas'], steps_of(name, prep))


def main() -> int:
    rows = [row.split('\t') for row in sys.stdin.read().splitlines() if row.count('\t') == 2]
    pipelines = {name: pipeline(name, None if prep == '-' else prep) for kind, name, prep in rows if kind == 'pipeline'}
    report = corpus.report_facts(None)
    for name, run in owed_runs().items():
        if name in pipelines:
            pipelines[name].remedy = run
    out = Status(pipelines, report.staged)
    out.now = facts.now_of(out) or facts.phrase('none - nothing to do')
    facts.say(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
