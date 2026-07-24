"""
model_curation.py — the model.json disposal loops' shared computation (issue #19).

rsc/schema/model.json is the hand-curated cross-pipeline type reference, and its
WORKFLOW step read "update if needed" — unfalsifiable: nothing reported that it
WAS needed, which is how the reference held one entry while model_join.csv grew
to 144 correspondence rows. The discipline is TWO loops with different pressure
(the PR #36 review, reading-room, directed by the user), both computed here from
committed files only, so every number is identical on any clone:

  1. leisurely, advisory → model_join. The naive name scan (definition names in
     >=2 families' latest versions) surfaces collisions a human curates into a
     model_join edge with a relationship kind, or ignores. No gate pressure, no
     disposal record — model_join IS the disposal record, and a name_collision
     kind records a false friend (same name, NOT one type: ContentBlock).
  2. blocking, gated model_join → model.json. An edge whose relationship kind
     denotes ONE shared type (identical, snake_cased) obligates model.json:
     the type is DOCUMENTED there or REJECTED with a reason in
     rsc/schema/model_rejected.txt. Reported per shared type by pre_commit's
     check_model_obligations (schema tier, gating) and by `yoga model`.

model_join is a typed relation — a small linked-data graph over the schema
corpus — and the model.json obligation is one consumer of certain predicates:
new relationship kinds join without touching the rule, and other consumers can
key off other predicates later.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO / 'rsc' / 'schema'
MODEL_JSON = SCHEMA_DIR / 'model.json'
MODEL_JOIN = SCHEMA_DIR / 'model_join.csv'
REJECTED = SCHEMA_DIR / 'model_rejected.txt'

JOIN_PATH_COLUMNS = ('conversations_path', 'session_path', 'apiConversation_path', 'mcp_path')
# The obligating predicates: kinds that assert ONE type shared across pipelines.
# subset is deliberately absent (related, not one type — a judgment call per
# edge); name_collision emphatically so (its notes record false friends).
OBLIGATING_KINDS = ('identical', 'snake_cased')


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


def _join_rows() -> list:
    with MODEL_JOIN.open() as fh:
        return list(csv.DictReader(fh))


def name_scan() -> dict:
    """{definition name: [families]} for names defined in >=2 families — the
    leisurely loop's raw material, run by anyone, anytime."""
    by_name = defaultdict(set)
    for fam, path in latest_versions().items():
        for name in json.loads(path.read_text()).get('definitions', {}):
            by_name[name].add(fam)
    return {n: sorted(f) for n, f in sorted(by_name.items()) if len(f) > 1}


def unrecorded_collisions() -> dict:
    """Scan hits no model_join path mentions — the leisurely loop's queue:
    curate each into an edge (assigning its relationship kind) or ignore."""
    recorded = set()
    for row in _join_rows():
        for col in JOIN_PATH_COLUMNS:
            m = re.search(r'#/definitions/([^/]+)', row[col] or '')
            if m:
                recorded.add(m.group(1))
    return {n: f for n, f in name_scan().items() if n not in recorded}


def obligating_edges() -> list:
    """[(csv row number, relationship, frozenset of definition names)] for every
    cross-pipeline edge whose kind asserts one shared type. The names are the
    containing definitions of each filled path (a property-level identical edge
    obligates its containing type)."""
    out = []
    for i, row in enumerate(_join_rows(), 2):
        filled = [row[c] for c in JOIN_PATH_COLUMNS if (row[c] or '').strip()]
        if len(filled) < 2 or row['relationship'] not in OBLIGATING_KINDS:
            continue
        names = frozenset(m.group(1) for v in filled
                          if (m := re.search(r'#/definitions/([^/]+)', v)))
        if names:
            out.append((i, row['relationship'], names))
    return out


def shared_types() -> dict:
    """{frozenset of names: [edge row numbers]} — the blocking loop's units: one
    obligation per distinct shared type, however many edges assert it."""
    out = defaultdict(list)
    for i, _kind, names in obligating_edges():
        out[names].append(i)
    return dict(out)


def documented() -> set:
    """Type names model.json documents (its `default` keys)."""
    return set(json.loads(MODEL_JSON.read_text()).get('default', {}))


def rejected() -> set:
    """Names in the disposal record: one per line, optional trailing '# reason',
    full-line '#' comments ignored."""
    if not REJECTED.exists():
        return set()
    out = set()
    for line in REJECTED.read_text().splitlines():
        name = line.split('#')[0].strip()
        if name:
            out.add(name)
    return out


def obligation_queue() -> dict:
    """Shared types with NO name documented or rejected — the blocking queue.
    Any name of the set disposes it (a snake_cased pair is one type under two
    dressings; documenting either is documenting the type)."""
    done = documented() | rejected()
    return {names: rows for names, rows in shared_types().items()
            if not (names & done)}
