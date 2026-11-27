"""
status.py - bare `corpus-yoga pipeline`: each pipeline by its declaration and the steps its
plan names, read as rows on stdin from pipeline.sh (`pipeline <name>`, tab-separated), then the stage's every unit by its facts, as one shape (issues/759, issues/800).
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
    act: facts.Would | None = None     # the run, for what it is owed one (issues/1005)


@dataclass
class Status:
    pipelines: dict[str, Pipeline]
    staged: dict[str, corpus.Staged]
    collate: facts.Would | None = None   # the collate, where no run is owed and it would act (issues/1188)
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


def owed_collate(owed: dict[str, facts.Would]) -> facts.Would | None:
    """The collate, where one is owed: no pipeline is owed a run, since the collate refuses while
    one is (issues/1183), and some unit's run output is not what the last collate read, by selection."""
    if owed:
        return None
    due: dict[str, int] = {}
    for name, declared in frontier.pipelines():
        for key, count in validation_audit.owed_collate_by_selection(name, declared).items():
            due[key] = due.get(key, 0) + count
    return facts.Would(spell.line('pipeline', 'collate'), due) if due else None


def steps_of(name: str) -> list[str]:
    """The steps the pipeline's plans name (`run.sh --plan`, then `run.sh --plan --collate`, the one
    authority on their order)."""
    plan = ''.join(subprocess.run([str(PIPELINE_ROOT / name / 'run.sh'), '--plan', *mode], capture_output=True, text=True, cwd=REPO).stdout
                   for mode in ([], ['--collate']))
    steps: list[str] = []
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


def pipeline(name: str) -> Pipeline:
    declared = json.loads((PIPELINE_ROOT / name / 'pipeline.json').read_text())
    providers = declared.get('provider')
    if providers:
        unit = one_or_each({p: v['unit'] for p, v in providers.items()})
        measure = one_or_each({p: v['measure'] for p, v in providers.items()})
    else:
        unit, measure = declared.get('unit'), declared.get('measure')
    return Pipeline(declared['input'], list(providers) if providers else None, unit or None, measure or None,
                    declared['schemas'], steps_of(name))


def main() -> int:
    rows = [row.split('\t') for row in sys.stdin.read().splitlines() if row.count('\t') == 1]
    pipelines = {name: pipeline(name) for kind, name in rows if kind == 'pipeline'}
    report = corpus.report_facts(None)
    owed = owed_runs()
    for name, run in owed.items():
        if name in pipelines:
            pipelines[name].act = run
    out = Status(pipelines, report.staged, owed_collate(owed))
    out.now = facts.now_of(out) or facts.phrase('none - nothing to do')
    facts.say(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
