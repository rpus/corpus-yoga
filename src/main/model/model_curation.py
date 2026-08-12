"""
model_curation.py — the model.json disposal loops' shared computation (issue #19).

rsc/schema/model.json is the hand-curated cross-family type reference, and its
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
     rsc/schema/model_rejected.txt. Reported per shared type by `yoga test run`'s
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

SELF = 'src/main/model/model_curation.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
SCHEMA_DIR = REPO / 'rsc' / 'schema'
MODEL_JSON = SCHEMA_DIR / 'model.json'
MODEL_JOIN = SCHEMA_DIR / 'model_join.csv'
REJECTED = SCHEMA_DIR / 'model_rejected.txt'

JOIN_PATH_COLUMNS = ('conversations_path', 'session_path', 'apiConversation_path', 'mcp_path')
# The obligating predicates: kinds that assert ONE type shared across families
# (usually across pipelines, but the account-uuid edge is intra-chat-exports —
# family is the grain, the PR #36 review's surviving nit). subset is
# deliberately absent (related, not one type — a judgment call per edge);
# name_collision emphatically so (its notes record false friends).
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


# model_join's path columns, by the family each addresses — the prefill's map.
# A collision touching a family outside these four still lists it in the
# worksheet's families column; the row's path cells carry what the table can.
COLUMN_FAMILY = {'conversations_path': 'chat-exports/conversations',
                 'session_path': 'code-agents/session',
                 'apiConversation_path': 'browser-captures/apiConversation',
                 'mcp_path': '_reference/mcp'}


def collision_candidates() -> list[dict]:
    """The leisurely queue as pre-filled model_join rows - machine proposes,
    human disposes: each undisposed cross-family name becomes a worksheet row
    with its path cells computed, leaving the two judgment fields (relationship,
    note) blank. Disposal is pasting the row into rsc/schema/model_join.csv
    with a kind - name_collision records a false friend - per
    rsc/schema/WORKFLOW.md's model_join review."""
    rows = []
    for name, families in unrecorded_collisions().items():
        row = {'name': name, 'families': ' '.join(families)}
        for column, family in COLUMN_FAMILY.items():
            row[column] = f'{family}#/definitions/{name}' if family in families else ''
        row['relationship'] = ''
        row['note'] = ''
        rows.append(row)
    return rows


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


STRUCTURAL_TOKENS = {'definitions', 'properties', 'items', 'prefixItems',
                     'oneOf', 'anyOf', 'allOf'}


def _schema_trail(fragment: str) -> tuple:
    """A schema path's property trail — the field names below its containing
    definition (or below the root, for inline shapes), structural tokens
    dropped: '#/definitions/Conversation/properties/account/properties/uuid'
    → ('account', 'uuid'); '#/items/properties/account_uuid' → ('account_uuid',)."""
    toks = [t for t in fragment.lstrip('#/').split('/') if t]
    if toks[:1] == ['definitions']:
        toks = toks[2:]
    return tuple(t for t in toks if t not in STRUCTURAL_TOKENS and not t.isdigit())


def _instance_trail(pointer: str) -> tuple:
    """An instance pointer's key trail, array indices dropped:
    '#/0/account/uuid' → ('account', 'uuid')."""
    return tuple(t for t in pointer.lstrip('#/').split('/') if t and not t.isdigit())


def obligating_edges() -> list:
    """[(csv row number, relationship, frozenset of names, {family: trail})] for
    every edge whose kind asserts one shared type. Names are the containing
    definitions of each filled path (a property-level identical edge obligates
    its containing type); trails carry the field identity for inline shapes a
    definition name cannot (the account-uuid edge)."""
    out = []
    for i, row in enumerate(_join_rows(), 2):
        filled = [row[c] for c in JOIN_PATH_COLUMNS if (row[c] or '').strip()]
        if len(filled) < 2 or row['relationship'] not in OBLIGATING_KINDS:
            continue
        names = frozenset(m.group(1) for v in filled
                          if (m := re.search(r'#/definitions/([^/]+)', v)))
        trails = {}
        for v in filled:
            fam, _, frag = v.partition('#')
            trails[fam] = _schema_trail(frag)
        if names or any(trails.values()):
            out.append((i, row['relationship'], names, trails))
    return out


def entries() -> dict:
    """{documented name: {family: [instance trails]}} from model.json."""
    doc = json.loads(MODEL_JSON.read_text()).get('default', {})
    return {name: {fam: [_instance_trail(p) for p in ptrs]
                   for fam, ptrs in e.get('occurrences', {}).items()}
            for name, e in doc.items()}


def grounds(edge, name: str, occ: dict) -> bool:
    """THE grounding relation, one rule read in both directions: an edge and an
    entry correspond iff the entry's name is one of the edge's containing
    definitions (definition-level types: TextContent), or some family carries
    equal trails on both sides (inline field types: the account uuid, whose
    semantic name — UserUUID — no schema definition can supply)."""
    _i, _kind, names, trails = edge
    if name in names:
        return True
    return any(fam in occ and trails[fam] and trails[fam] in occ[fam]
               for fam in trails)


def _edge_key(names: frozenset, trails: dict) -> frozenset:
    return names or frozenset('/'.join(t) for t in trails.values() if t)


def shared_types() -> dict:
    """{frozenset of names (or trail labels): [edge row numbers]} — the
    edge→doc direction's units: one obligation per distinct shared type,
    however many edges assert it."""
    out = defaultdict(list)
    for i, _kind, names, trails in obligating_edges():
        out[_edge_key(names, trails)].append(i)
    return dict(out)


def edge_queue() -> dict:
    """edge→doc: shared types no documented entry grounds and no rejection
    covers — the blocking queue."""
    ents = entries()
    rej = rejected()
    out = defaultdict(list)
    for edge in obligating_edges():
        i, _kind, names, trails = edge
        if names & rej:
            continue
        if any(grounds(edge, n, occ) for n, occ in ents.items()):
            continue
        out[_edge_key(names, trails)].append(i)
    return dict(out)


def orphan_entries() -> list:
    """doc→edge: documented types no obligating edge grounds — orphan
    documentation, the reverse direction (the PR #36 review's gap: UserUUID
    passed the one-directional gate on no recorded basis). With edge_queue
    empty and this empty, model.json documents exactly what model_join
    asserts, minus rejections."""
    edges = obligating_edges()
    return sorted(name for name, occ in entries().items()
                  if not any(grounds(e, name, occ) for e in edges))


def coverage_gaps() -> dict:
    """{documented name: sorted [data families a grounding edge asserts but the
    entry's occurrences omit]}. grounds() needs only ONE family to match, so a
    type can ground with a dressing missing and still pass — and then model.json
    answers "where does this type occur" incompletely, which is the non-foolproof
    grep the user named: the account uuid wears four dressings (account.uuid /
    account_uuid / uuid / creator.uuid), no substring search unifies them, so the
    index must be the reliable answer the schemas cannot be. Completeness is over
    DATA families only — an occurrence is an instance pointer into a datum, and a
    _reference schema (mcp) has no datum, so its correspondence lives in the edge,
    not here (latest_versions() already excludes _-prefixed reference schemas).
    With edge_queue, orphan_entries, and this all empty, model.json is the
    complete, foolproof type-occurrence index."""
    data_families = set(latest_versions())
    ents = entries()
    gaps = defaultdict(set)
    for edge in obligating_edges():
        _i, _kind, _names, trails = edge
        asserted = set(trails) & data_families
        for name, occ in ents.items():
            if grounds(edge, name, occ):
                gaps[name] |= asserted - set(occ)
    return {n: sorted(f) for n, f in gaps.items() if f}


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


