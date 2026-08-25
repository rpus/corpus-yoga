#!/usr/bin/env python
"""
frontier.py - the corpus's shape as the data gate reads it: the pipelines and
their declared facts (pipelines()), each pipeline's subject dirs under its
tmp/cache workshop (subject_dirs), and a family's versions in numeric order
(sorted_versions). Read-only. The frontier verdict itself - every datum
validates at its family's latest version - is the audit's (#557,
src/main/validation_audit.py), stated per datum from the latest version's log.

Recency is pipeline-specific because the corpora differ: chat-exports orders
by its export-dir name's vintage (supersede's export_time, the one ordering
authority over rsc/naming/export_dir_vintages.csv); browser-captures the
capture's updated_at; code-agents the max record timestamp in the session
.jsonl. Keys compare only within one pipeline, so mixed key types across
pipelines are fine.

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
sys.path.insert(0, str(REPO / 'src' / 'main' / 'pipeline' / 'chat-exports'))  # supersede - the one export-ordering authority
import cache_io  # noqa: E402
from supersede import export_time  # noqa: E402

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


def pipelines():
    """(name, facts) for every declared pipeline - membership is placement (#327)."""
    for d in sorted(PIPELINE_ROOT.iterdir()):
        f = d / 'pipeline.json'
        if f.is_file():
            yield d.name, json.loads(f.read_text())


