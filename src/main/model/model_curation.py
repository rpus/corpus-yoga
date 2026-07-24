"""
model_curation.py — the model.json disposal loop's shared computation (issue #19).

rsc/schema/model.json is the hand-curated CROSS-PIPELINE type reference, and its
WORKFLOW step read "update if needed" — unfalsifiable: nothing reported that it
WAS needed, which is how the reference held one entry while model_join.csv grew
144 correspondence rows. This module makes the need a number, indexing's shape
(the `curate` operation, rsc/CALCULUS.md):

  candidates — definition names shared by >=2 schema families (each family's
               latest version): the cross-pipeline types model.json's own
               description promises. A single-family definition is not a
               cross-pipeline correspondence and never enters the queue.
  disposal   — DOCUMENT the name in rsc/schema/model.json, or DISMISS it with
               a reason in rsc/schema/model_dismissed.txt.
  pending    — candidates minus disposed; reported by `yoga model` and the
               pre_commit advisory (check_model_curation), never silent.

Committed inputs only, so the queue is identical on any clone. Consumed by
gen_model.py (the status surface) and src/test/pre_commit.py (the advisory and
the occurrence checks).
"""
import json
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO / 'rsc' / 'schema'
MODEL_JSON = SCHEMA_DIR / 'model.json'
DISMISSED = SCHEMA_DIR / 'model_dismissed.txt'


def latest_versions() -> dict:
    """{'<pipeline>/<family>': its latest vN.json} over every versioned family."""
    out = {}
    for pipe in sorted(SCHEMA_DIR.iterdir()):
        if not pipe.is_dir() or pipe.name.startswith('_'):
            continue
        for fam in sorted(pipe.iterdir()):
            if not fam.is_dir():
                continue
            versions = sorted(fam.glob('v*.json'),
                              key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)])
            if versions:
                out[f'{pipe.name}/{fam.name}'] = versions[-1]
    return out


def candidates() -> dict:
    """{definition name: [families defining it]}, names defined in >=2 families,
    name-sorted — the machine-proposed half of the disposal loop."""
    by_name = defaultdict(set)
    for fam, path in latest_versions().items():
        for name in json.loads(path.read_text()).get('definitions', {}):
            by_name[name].add(fam)
    return {n: sorted(f) for n, f in sorted(by_name.items()) if len(f) > 1}


def documented() -> set:
    """Type names model.json documents (its `default` keys)."""
    return set(json.loads(MODEL_JSON.read_text()).get('default', {}))


def dismissed() -> set:
    """Names in the disposal record: one per line, optional trailing '# reason',
    full-line '#' comments ignored."""
    if not DISMISSED.exists():
        return set()
    out = set()
    for line in DISMISSED.read_text().splitlines():
        name = line.split('#')[0].strip()
        if name:
            out.add(name)
    return out


def pending() -> dict:
    """The queue: candidates neither documented nor dismissed."""
    done = documented() | dismissed()
    return {n: fams for n, fams in candidates().items() if n not in done}
