#!/usr/bin/env python
"""
frontier.py - the corpus frontier, one fact per schema family: does the NEWEST
datum validate under the family's LATEST version? Read-only, and no new
validation: verdicts are read from the vN.logs each pipeline's validate step
already wrote under its tmp/cache workshop (leaf/validation/<family>/<vN>.log).

Recency is pipeline-specific because the corpora differ: chat-exports carries
the epoch in the batch dir name; browser-captures the capture's updated_at;
code-agents the max record timestamp in the session .jsonl. Keys compare only
within one pipeline, so mixed key types across pipelines are fine.

Consumers: model.py (bare `corpus-yoga model` states each family's verdict, so the
usr gate's corpus tail says it - #373) and src/test/dev/run.py (the data-tier
frontier and coverage checks read subjects and recency from here).
"""
import json
import re
import sys
from pathlib import Path

SELF = 'src/main/model/frontier.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'cache'))  # cache_io - the declared tmp/cache IO registry
import cache_io  # noqa: E402

PIPELINE_ROOT = REPO / 'src' / 'main' / 'pipeline'
SCHEMA_ROOT = REPO / 'rsc' / 'schema'


def sorted_versions(schema_dir):
    """v*.json files in numeric order - the last is the family's latest."""
    return sorted(schema_dir.glob('v*.json'),
                  key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)])


def subject_dirs(cache_root, depth):
    """Yield (subject, leaf_dir) for each subject directory under a pipeline's
    cache root, at its declared depth (subject = ' / '-joined path parts)."""
    if not cache_root.exists():
        return
    for leaf in sorted(cache_root.glob('/'.join(['*'] * depth))):
        if leaf.is_dir():
            yield ' / '.join(leaf.relative_to(cache_root).parts), leaf


def datum_recency(pipeline_name, input_root, subject):
    """A sortable recency key for one datum, or None if unavailable. Keys are
    only ever compared within a single pipeline."""
    if pipeline_name == 'chat-exports':
        m = re.search(r'-(\d{10})-[0-9a-f]+-batch', subject)
        return int(m.group(1)) if m else None
    if pipeline_name == 'browser-captures':
        f = input_root / subject / f'{subject}.json'
        try:
            return json.loads(f.read_text()).get('updated_at')
        except (OSError, ValueError):
            return None
    if pipeline_name == 'code-agents':
        f = input_root.joinpath(*subject.split(' / ')).with_suffix('.jsonl')
        try:
            lines = f.read_text().splitlines()
        except OSError:
            return None
        stamps = []
        for line in lines:
            try:
                t = json.loads(line).get('timestamp')
            except ValueError:
                continue
            if t:
                stamps.append(t)
        return max(stamps) if stamps else None
    return None


def pipelines():
    """(name, facts) for every declared pipeline - membership is placement (#327)."""
    for d in sorted(PIPELINE_ROOT.iterdir()):
        f = d / 'pipeline.json'
        if f.is_file():
            yield d.name, json.loads(f.read_text())


def _family_units(leaf, family):
    """The vN.log homes for one family under one subject leaf: the family dir
    itself, or its per-item subdirectories (chat-exports' projects validate as
    validation/projects/<project-uuid>/vN.log - one datum, many items)."""
    d = leaf / 'validation' / family
    if not d.is_dir():
        return []
    subs = [s for s in sorted(d.iterdir()) if s.is_dir()]
    return subs if subs else [d]


def verdicts():
    """One record per (pipeline, family): the newest datum's standing against
    the family's latest version. A family's candidate subjects are those
    holding its evidence (a validation/<family>/ dir) - families partition a
    pipeline's subjects (code-agents' projectMemory lives on memory/ dirs,
    never on sessions). Where recency is unknown for every candidate, every
    datum is checked instead of a false newest being picked (scope 'all').
    kind: 'green' | 'red' | 'no-datum'."""
    for name, facts in pipelines():
        cache_root = REPO / cache_io.path_for(name)
        input_root = REPO / facts['input']
        subjects = list(subject_dirs(cache_root, facts['subject_depth']))
        for family in facts['schemas']:
            versions = sorted_versions(SCHEMA_ROOT / name / family)
            if not versions:
                continue
            latest = versions[-1].stem
            candidates = [(datum_recency(name, input_root, subject), subject, leaf)
                          for subject, leaf in subjects
                          if (leaf / 'validation' / family).is_dir()]
            if not candidates:
                yield {'pipeline': name, 'family': family, 'latest': latest,
                       'kind': 'no-datum', 'subject': None, 'log': None,
                       'scope': 'none', 'count': 0}
                continue
            # tuple, unparameterized: the key's type is per-pipeline (epoch int
            # or ISO string), and the None-filter here is what makes max total
            keyed: list[tuple] = [c for c in candidates if c[0] is not None]
            if keyed:
                chosen, scope = [max(keyed, key=lambda c: c[0])], 'newest'
            else:
                chosen, scope = candidates, 'all'
            bad = None
            for _, subject, leaf in chosen:
                for unit in _family_units(leaf, family):
                    log = unit / f'{latest}.log'
                    if not (log.exists() and 'Valid!' in log.read_text()):
                        item = subject if unit.name == family else f'{subject} / {unit.name}'
                        bad = (item, log.relative_to(REPO))
                        break
                if bad:
                    break
            yield {'pipeline': name, 'family': family, 'latest': latest,
                   'kind': 'red' if bad else 'green',
                   'subject': bad[0] if bad else (chosen[0][1] if scope == 'newest' else None),
                   'log': bad[1] if bad else None,
                   'scope': scope, 'count': len(chosen)}
