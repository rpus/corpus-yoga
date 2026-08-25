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
     rsc/schema/model_rejected.txt. Reported per shared type by `corpus-yoga test run`'s
     check_model_obligations (schema tier, gating) and by `corpus-yoga model`.

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


KINDS_TABLE = SCHEMA_DIR / 'model_join_kinds.csv'


def kinds() -> dict:
    """{kind: claim_class} from the declared vocabulary - the relationship
    column's one authority (rsc/schema/model_join_kinds.csv)."""
    with KINDS_TABLE.open(newline='') as fh:
        return {r['kind']: r['claim_class'] for r in csv.DictReader(fh)}


def undeclared_kinds() -> list:
    """model_join rows whose relationship names no declared kind - each is a
    typo or a vocabulary gap, and either way the kinds table rules first."""
    declared = kinds()
    return [(i, row['relationship']) for i, row in enumerate(_join_rows(), 2)
            if row['relationship'] not in declared]


def _resolve(cell: str):
    """A model_join cell's fragment resolved in its family's LATEST version -
    the join's one grammar: any family dir relative to rsc/schema,
    _reference/mcp included, resolved against its own latest vN.json. None
    when the cell is empty (an absence claim, not a pointer)."""
    if not cell:
        return None
    family, _, fragment = cell.partition('#')
    versions = sorted((SCHEMA_DIR / family).glob('v*.json'),
                      key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)])
    doc = json.loads(versions[-1].read_text())
    node = doc
    for token in fragment.lstrip('/').split('/'):
        node = node[token] if isinstance(node, dict) else node[int(token)]
    return _deref(node, doc)


def _deref(node, doc):
    """Local $ref indirections resolved against the node's own document, and the
    vacuous `additionalProperties: {}` (draft-04's no-constraint, spelled out)
    dropped - so a mint that merely NAMES a shared shape ({"$ref": ...}) falsifies
    no identity edge, and only a changed constraint can (#527's spurious class)."""
    if isinstance(node, dict):
        if isinstance(node.get('$ref'), str) and node['$ref'].startswith('#/'):
            target = doc
            for token in node['$ref'][2:].split('/'):
                target = target[token]
            merged = {k: v for k, v in node.items() if k != '$ref'}
            resolved = _deref(target, doc)
            overlay = _deref(merged, doc) if merged else None
            if isinstance(resolved, dict) and isinstance(overlay, dict):
                return {**resolved, **overlay}
            return resolved
        return {k: _deref(v, doc) for k, v in node.items()
                if not (k == 'additionalProperties' and v == {})}
    if isinstance(node, list):
        return [_deref(v, doc) for v in node]
    return node


DOCUMENTATION_KEYS = ('description', 'title', 'examples', '$comment')


def _identity_normalized(node):
    """The shape reduced to its constraints, the way the curators judged
    identity: documentation keys dropped, const spelled as its one-element
    enum, order-free lists (enum, required) sorted - so two spellings of one
    constraint compare equal and a description edit falsifies nothing."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key in DOCUMENTATION_KEYS:
                continue
            if key == 'const':
                out['enum'] = [_identity_normalized(value)]
                continue
            value = _identity_normalized(value)
            if key in ('enum', 'required') and isinstance(value, list):
                value = sorted(value, key=json.dumps)
            out[key] = value
        return out
    if isinstance(node, list):
        return [_identity_normalized(v) for v in node]
    return node


def _snake_normalized(node):
    """The shape with every mapping key case-folded and separator-stripped, so
    snake_cased identity compares spelling-blind."""
    if isinstance(node, dict):
        return {k.replace('_', '').lower(): _snake_normalized(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_snake_normalized(v) for v in node]
    return node


def identity_violations() -> list:
    """Edges whose kind asserts one shape (claim_class identity) where the
    filled cells no longer resolve to equal definitions at latest - a
    one-sided mint falsifies the edge silently, and this is where it stops
    being silent. snake_cased compares key-normalized."""
    identity_kinds = {k for k, c in kinds().items() if c == 'identity'}
    out = []
    for i, row in enumerate(_join_rows(), 2):
        if row['relationship'] not in identity_kinds:
            continue
        cells = [row[c] for c in JOIN_PATH_COLUMNS if row[c]]
        shapes = [_identity_normalized(_resolve(c)) for c in cells]
        if row['relationship'] == 'snake_cased':
            shapes = [_snake_normalized(s) for s in shapes]
        if any(s != shapes[0] for s in shapes[1:]):
            out.append((i, row['relationship'], ' § '.join(cells)))
    return out


# model_join's path columns, by the family each addresses — the prefill's map.
# A collision touching a family outside these four still lists it in the
# worksheet's families column; the row's path cells carry what the table can.
COLUMN_FAMILY = {'conversations_path': 'chat-exports/conversations',
                 'session_path': 'code-agents/session',
                 'apiConversation_path': 'browser-captures/apiConversation',
                 'mcp_path': '_reference/mcp'}


def shared_name_candidates() -> list[dict]:
    """The leisurely queue as pre-filled model_join rows - machine proposes,
    human disposes: each undisposed SHARED NAME (the scan-level question)
    becomes a worksheet row with its path cells computed. The relationship
    cell is the human's verdict - name_collision being the false-friend
    answer, one among the declared kinds - and stays blank except where the
    comparison is mechanical: same-name definitions structurally equal at
    latest prefill 'identical' as an editable proposal."""
    rows = []
    latest = latest_versions()
    for name, families in unrecorded_collisions().items():
        row = {'name': name, 'families': ' '.join(families)}
        for column, family in COLUMN_FAMILY.items():
            row[column] = f'{family}#/definitions/{name}' if family in families else ''
        shapes = []
        for family in families:
            if family in latest:
                doc = json.loads(latest[family].read_text())
                shapes.append(_identity_normalized(_deref(doc['definitions'][name], doc)))
        equal = len(shapes) > 1 and all(s == shapes[0] for s in shapes[1:])
        row['relationship'] = 'identical' if equal else ''
        row['note'] = 'machine proposal: structurally equal at latest - edit freely' if equal else ''
        rows.append(row)
    return rows


WORKSHEET = REPO / 'tmp' / 'cache' / 'model' / 'shared_name_candidates.csv'


def worksheet_rows() -> list[dict] | None:
    """The rendered worksheet as read - the queue accept/reject dispose. Refused
    (None) when absent or stale against a fresh computation: a disposal must act
    on the queue the reader saw, never on one that moved beneath them."""
    if not WORKSHEET.exists():
        return None
    rows = list(csv.DictReader(WORKSHEET.open()))
    return rows if rows == shared_name_candidates() else None


def _append_join_row(row: dict, relationship: str, note: str) -> None:
    """One disposal, one appended model_join.csv row - the worksheet's path
    cells verbatim, the relationship and note the disposal's two fields."""
    with MODEL_JOIN.open('a', newline='') as fh:
        csv.writer(fh).writerow([row['conversations_path'], row['session_path'],
                                  row['apiConversation_path'], row['mcp_path'],
                                  relationship, note])


def accept_shared_name(row: dict, date: str) -> str:
    """Adopt the machine proposal: the pre-filled row lands in model_join.csv
    with its proposed kind. A row without a proposal (divergent shapes) is
    refused - that judgment is the curator's (or paid capture's, #471)."""
    if not row['relationship']:
        return (f"refused: {row['name']} carries no machine proposal - the shapes "
                'diverge; judge the relationship kind by hand (rsc/schema/model_join_kinds.csv)')
    _append_join_row(row, row['relationship'],
                     f"adopted {date} from the worksheet's machine proposal: "
                     'structurally equal at latest')
    return f"accepted: {row['name']} - {row['relationship']} row appended to {MODEL_JOIN.relative_to(REPO)}"


def reject_shared_name(row: dict, reason: str, date: str) -> str:
    """Record the false friend: a name_collision row with the reason as its
    note - the rich-record twin of indexing's rejected.txt."""
    note = f'rejected {date}: {reason}' if reason else f'rejected {date}'
    _append_join_row(row, 'name_collision', note)
    return f"rejected: {row['name']} - name_collision row appended to {MODEL_JOIN.relative_to(REPO)}"


def occurrence_pointer(doc: dict, name: str):
    """An instance pointer to where definition `name` instantiates, derived by
    walking the schema from its root (properties -> key, items -> 0, $ref
    followed, oneOf/anyOf/allOf searched) to the first $ref of the definition -
    generated, never hand-written, so model.json occurrences cannot be fiction.
    None when the definition is unreachable from the root."""
    target = f'#/definitions/{name}'
    seen = set()

    def walk(node, trail):
        if isinstance(node, dict):
            ref = node.get('$ref')
            if ref == target:
                return trail
            if isinstance(ref, str) and ref.startswith('#/'):
                if ref in seen:
                    return None
                seen.add(ref)
                resolved = doc
                for token in ref[2:].split('/'):
                    resolved = resolved[token]
                found = walk(resolved, trail)
                if found is not None:
                    return found
                seen.discard(ref)
                return None
            for key, sub in node.get('properties', {}).items():
                found = walk(sub, trail + [key])
                if found is not None:
                    return found
            items = node.get('items')
            if isinstance(items, dict):
                found = walk(items, trail + ['0'])
                if found is not None:
                    return found
            for comb in ('oneOf', 'anyOf', 'allOf'):
                for branch in node.get(comb, []):
                    found = walk(branch, trail)
                    if found is not None:
                        return found
        return None

    trail = walk(doc, [])
    return None if trail is None else '#/' + '/'.join(trail)


def emptiness_violations(repo: Path) -> list:
    """Corpus evidence against the emptiness edges (null_in_api,
    null_in_export): a datum carrying a value at the pointed field falsifies
    the always-null note. An object instantiates the definition when the
    definition's required keys are a subset of its own; the scan names the
    first falsifying file per edge. Rooms without the relevant corpus skip,
    stated by the caller."""
    doc_roots = {'null_in_api': repo / 'data' / 'input' / 'claude' / 'chat' / 'browser-API',
                 'null_in_export': repo / 'tmp' / 'cache' / 'chat-exports'}
    emptiness_kinds = {k for k, c in kinds().items() if c == 'emptiness'}
    out = []
    for i, row in enumerate(_join_rows(), 2):
        if row['relationship'] not in emptiness_kinds:
            continue
        cell = next(row[c] for c in JOIN_PATH_COLUMNS if row[c])
        family, _, fragment = cell.partition('#')
        field = fragment.rsplit('/', 1)[-1]
        definition = _resolve(cell.split('/properties/')[0])
        assert definition is not None  # the cell was chosen non-empty
        required = set(definition.get('required') or [])
        root = doc_roots[row['relationship']]
        if not root.is_dir():
            continue
        hit = _first_value_bearing(root, required, field)
        if hit:
            out.append((i, row['relationship'], cell, str(hit.relative_to(repo))))
    return out


def _first_value_bearing(root: Path, required: set, field: str):
    """The first json under root holding an object that instantiates the
    definition (required keys a subset) with a NON-NULL value at field."""
    def walk(node):
        if isinstance(node, dict):
            if required <= set(node) and node.get(field) is not None and field in node:
                return True
            return any(walk(v) for v in node.values())
        if isinstance(node, list):
            return any(walk(v) for v in node)
        return False
    for doc in sorted(root.rglob('*.json')):
        try:
            if walk(json.loads(doc.read_text())):
                return doc
        except (OSError, ValueError):
            continue
    return None


def unrecorded_collisions() -> dict:
    """Shared names no model_join path mentions - the leisurely loop's queue:
    each disposes as an edge whose relationship kind is the verdict
    (name_collision records the false friend)."""
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


