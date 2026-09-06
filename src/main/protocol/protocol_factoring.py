#!/usr/bin/env python
"""
protocol_factoring.py - the house factoring of the MCP schema (#562): the composition
upstream's generator flattens, stated once in draft-04, derived from the verbatim
snapshot rsc/schema/_reference/mcp and written to rsc/schema/protocol/mcpMessage.

Upstream's schema.json inlines every message's envelope (jsonrpc, id, method,
params) because its TypeScript-to-JSON generator flattens `extends`. The composition
is hand-authored data: composition.csv (definition, base), transcribed from
schema.ts's `extends` at the pinned commit, and each row is VERIFIED against the
snapshot before it is used - adding the base's constraints to the definition must
change nothing (the definition refines the base) - so a row the data does not bear
refuses the derivation rather than misstating a subtype. A definition is then
written as allOf [bases..., its own fields]. Two bases upstream never names are
declared here: JSONRPCHeader (the version pin) and JSONRPCIdentifiedHeader (header
plus id); the table's envelope rows name them, because JSON Schema's allOf conjoins
and cannot narrow the open `params` of the generic JSONRPCRequest the way `extends`
does - the one place the factoring and schema.ts diverge, by necessity.

The witness is `disagreements()`: every snapshot definition, and its house
counterpart flattened (allOf merged, refs resolved) - both normalized (documentation
dropped, const as one-element enum, the vacuous additionalProperties {} dropped,
order-free lists sorted) - must compare equal. The dev gate holds it.
"""

import csv
import json
import re
import sys
from pathlib import Path

SELF = 'src/main/protocol/protocol_factoring.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))  # src/ - modules both tiers import
from schema_walk import schema_nodes, SCHEMA_MAPS, SCHEMA_LISTS, SCHEMA_SINGLETONS  # noqa: E402

SNAPSHOT_DIR = REPO / 'rsc/schema/_reference/mcp'
FAMILY_DIR   = REPO / 'rsc/schema/protocol/mcpMessage'
DESCRIPTIONS = FAMILY_DIR / 'description.csv'
COMPOSITION  = FAMILY_DIR / 'composition.csv'
FAMILY       = 'mcpMessage'
ROOT_DEFINITION = 'JSONRPCMessage'
DRAFT_04 = 'http://json-schema.org/draft-04/schema#'

DOCUMENTATION_KEYS = ('title', 'description', '$comment', 'examples')
KEY_ORDER = ('title', 'description', 'type', 'allOf', 'anyOf', 'oneOf', '$ref', 'enum',
             'format', 'pattern', 'minimum', 'maximum', 'minLength', 'maxLength',
             'minItems', 'maxItems', 'items', 'properties', 'required',
             'additionalProperties', 'default')
EXHAUSTIVE_CLAUSE = 'The values are exhaustive: those the MCP {lineage} spec enumerates.'

# The two bases upstream never names - the design the factoring adds. Shapes are
# flat (like every snapshot definition); the composition below factors them too.
SYNTHETIC_BASES = {
    'JSONRPCHeader': {
        'description': 'The JSON-RPC 2.0 header every message carries: the protocol '
                       'version pin. Declared once here; upstream inlines it per message.',
        'type': 'object',
        'properties': {'jsonrpc': {'type': 'string', 'enum': ['2.0']}},
        'required': ['jsonrpc'],
    },
    'JSONRPCIdentifiedHeader': {
        'description': 'The header plus the id that correlates a request with its '
                       'response - what requests and result responses share.',
        'type': 'object',
        'properties': {'jsonrpc': {'type': 'string', 'enum': ['2.0']},
                       'id': {'$ref': '#/definitions/RequestId'}},
        'required': ['id', 'jsonrpc'],
    },
}


# ── inputs ────────────────────────────────────────────────────────────────────

def latest_version(family_dir: Path):
    versions = sorted(family_dir.glob('v*.json'),
                      key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)])
    return versions[-1] if versions else None


def snapshot() -> tuple[Path, dict]:
    path = latest_version(SNAPSHOT_DIR)
    assert path, f'{SNAPSHOT_DIR.relative_to(REPO)} holds no v*.json'
    return path, json.loads(path.read_text())


def provenance() -> dict:
    """The snapshot's pinned lineage URL, commit and SHA256, read from its changelog
    section - the one home the snapshot family gives them (#561)."""
    path = latest_version(SNAPSHOT_DIR)
    assert path, f'{SNAPSHOT_DIR.relative_to(REPO)} holds no v*.json'
    text = (SNAPSHOT_DIR / 'CHANGELOG.md').read_text()
    m = re.search(rf'^## {path.stem}$(.*?)(?=^## |\Z)', text, re.M | re.S)
    section = m.group(1) if m else ''
    url = re.search(r'(https://raw\.githubusercontent\.com/\S+?/schema/(\d{4}-\d{2}-\d{2})/schema\.json)', section)
    commit = re.search(r'as at commit:\s*`?([0-9a-f]{40})', section)
    sha = re.search(r'upstream SHA256:\s*`?([0-9a-f]{64})', section)
    assert url and commit and sha, f'the ## {path.stem} section of the snapshot changelog pins no provenance triple'
    raw_url, lineage = url.group(1), url.group(2)
    return {'url': raw_url, 'lineage': lineage, 'commit': commit.group(1), 'sha256': sha.group(1),
            'ts_url': raw_url.replace('/refs/heads/main/', f'/{commit.group(1)}/').replace('schema.json', 'schema.ts')}


def composition() -> dict[str, list[str]]:
    """{definition: [base, ...]} - the declared composition, transcribed from
    schema.ts and verified against the snapshot at derivation."""
    if not COMPOSITION.exists():
        return {}
    out: dict[str, list[str]] = {}
    with COMPOSITION.open(newline='') as fh:
        for row in csv.DictReader(fh):
            out.setdefault(row['definition'], []).append(row['base'])
    return out


def descriptions() -> dict:
    """Hand-authored descriptions for the definitions the snapshot leaves
    undescribed - the family's data, beside its versions."""
    if not DESCRIPTIONS.exists():
        return {}
    with DESCRIPTIONS.open(newline='') as fh:
        return {row['name']: row['description'] for row in csv.DictReader(fh)}


# ── schema algebra ────────────────────────────────────────────────────────────

def _mapped(node: dict, keywords) -> dict:
    """node with `keywords` applied at every schema position - a shallow rewrite of
    one schema dict's keys - descending only into schema positions (schema_walk's
    grammar), so a property named const, enum or $ref is a name, never a keyword."""
    out = {}
    for key, value in keywords(node).items():
        if key in SCHEMA_MAPS and isinstance(value, dict):
            out[key] = {name: _mapped(sub, keywords) for name, sub in value.items()}
        elif key in SCHEMA_LISTS and isinstance(value, list):
            out[key] = [_mapped(sub, keywords) for sub in value]
        elif key == 'items':
            out[key] = ([_mapped(sub, keywords) for sub in value] if isinstance(value, list)
                        else _mapped(value, keywords) if isinstance(value, dict) else value)
        elif key in SCHEMA_SINGLETONS and isinstance(value, dict):
            out[key] = _mapped(value, keywords)
        else:
            out[key] = value
    return out


def _house_keywords(node: dict) -> dict:
    out = {}
    for key, value in node.items():
        if key == '$ref' and isinstance(value, str):
            out[key] = value.replace('#/$defs/', '#/definitions/')
        elif key == 'const':
            out['enum'] = [value]
        else:
            out[key] = value
    return out


def to_house(node: dict) -> dict:
    """The snapshot's dialect spelled in draft-04: $defs refs to definitions, const
    to its one-element enum - at schema positions only. Content-preserving."""
    return _mapped(node, _house_keywords)


def _normal_keywords(node: dict) -> dict:
    out = {}
    for key, value in node.items():
        if key in DOCUMENTATION_KEYS:
            continue
        if key == 'const':
            out['enum'] = [value]
            continue
        if key == 'additionalProperties' and value == {}:
            continue
        if key == '$ref' and isinstance(value, str):
            out[key] = value.split('/')[-1]
            continue
        if key in ('enum', 'required') and isinstance(value, list):
            value = sorted(value, key=json.dumps)
        out[key] = value
    return out


def normalized(node: dict) -> dict:
    """The comparison form: documentation dropped, const as enum, the vacuous
    additionalProperties {} dropped, refs by definition name, order-free lists
    (enum, required) sorted - two spellings of one constraint compare equal, and
    only keywords are rewritten, never a property that shares a keyword's name."""
    return _mapped(node, _normal_keywords)


class Conflict(ValueError):
    """Two constraints on one key that cannot both hold as one schema value."""


def merged(a: dict, b: dict) -> dict:
    """The conjunction of two schema dicts as one dict: keys unite, shared keys must
    agree - dicts conjoin recursively (properties maps and subschemas alike),
    `required` unites, documentation takes the later value, anything else that
    differs is a Conflict (the conjunction has no single-dict spelling)."""
    out = dict(a)
    for key, value in b.items():
        if key not in out or out[key] == value:
            out[key] = value
        elif key in DOCUMENTATION_KEYS:
            out[key] = value
        elif key == 'required':
            out[key] = out[key] + [x for x in value if x not in out[key]]
        elif isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = merged(out[key], value)
        else:
            raise Conflict(f'{key}: {json.dumps(out[key])} vs {json.dumps(value)}')
    return out


def flattened(defn: dict, definitions: dict, _seen=()) -> dict:
    """A definition with its allOf resolved: each member (a $ref to a definition, or
    an inline schema) flattened and conjoined, then the definition's own keys."""
    if 'allOf' not in defn:
        return defn
    acc: dict = {}
    for member in defn['allOf']:
        if '$ref' in member:
            name = member['$ref'].split('/')[-1]
            assert name not in _seen, f'allOf cycle through {name}'
            part = flattened(definitions[name], definitions, _seen + (name,))
        else:
            part = flattened(member, definitions, _seen)
        acc = merged(acc, part)
    own = {k: v for k, v in defn.items() if k != 'allOf'}
    return merged(acc, own)


def refines(base: dict, defn: dict) -> bool:
    """True when adding base's constraints to defn changes nothing - defn already
    says everything base says (and more: identical shapes are not a refinement)."""
    n_base, n_defn = normalized(base), normalized(defn)
    if n_base == n_defn:
        return False
    try:
        return normalized(merged(base, defn)) == n_defn
    except Conflict:
        return False


# ── the factoring ─────────────────────────────────────────────────────────────

def _ordered(defn: dict) -> dict:
    rank = {k: i for i, k in enumerate(KEY_ORDER)}
    return {k: defn[k] for k in sorted(defn, key=lambda k: (rank.get(k, len(KEY_ORDER)), k))}


def _composed(name: str, flat: dict, bases: list[str], shapes: dict) -> dict:
    """flat, rewritten as allOf [bases..., own fields]: a property a base supplies
    identically is omitted, a property the definition refines or adds stays,
    required keeps what no base requires."""
    if not bases:
        return dict(flat)
    supplied_props: dict = {}
    supplied_required: list = []
    for b in bases:
        supplied_props.update(shapes[b].get('properties', {}))
        supplied_required += shapes[b].get('required', [])
    own = {k: v for k, v in flat.items() if k not in ('properties', 'required')}
    required = [r for r in flat.get('required', []) if r not in supplied_required]
    # a property stays when no base supplies it identically, or when this definition
    # requires it and no base does - `required` names only local properties
    props = {p: s for p, s in flat.get('properties', {}).items()
             if p not in supplied_props or normalized(supplied_props[p]) != normalized(s)
             or p in required}
    own['allOf'] = [{'$ref': f'#/definitions/{b}'} for b in bases]
    if props:
        own['properties'] = props
    if required:
        own['required'] = required
    return own


def _document_enums(definitions: dict, lineage: str) -> None:
    clause = EXHAUSTIVE_CLAUSE.format(lineage=lineage)
    for defn in definitions.values():
        for _, node in schema_nodes(defn):
            if isinstance(node.get('enum'), list) and len(node['enum']) > 1:
                text = node.get('description', '')
                if not any(w in text.lower() for w in ('exhaustive', 'open set', 'discriminator')):
                    node['description'] = (text + ' ' + clause).strip()


def _bfs_order(definitions: dict, root: str) -> list[str]:
    """Breadth-first referential encounter order from root, the unreachable after,
    alphabetical - the order structure.bfs_order asks of every house schema."""
    def refs_in(node):
        out = []
        for _, sub in schema_nodes(node):
            if isinstance(sub.get('$ref'), str):
                r = sub['$ref'].split('/')[-1]
                if r not in out:
                    out.append(r)
        return out
    order, seen, queue = [], set(), [root]
    while queue:
        n = queue.pop(0)
        if n in seen:
            continue
        seen.add(n)
        order.append(n)
        queue += [r for r in refs_in(definitions[n]) if r not in seen and r in definitions]
    return order + sorted(n for n in definitions if n not in seen)


def factored(snapshot_doc: dict, described: dict, composed: dict, prov: dict) -> dict:
    """The house schema, whole: every snapshot definition composed over its bases,
    the two synthetic headers, titles and descriptions per house rule, definitions
    in BFS order, the root the wire message."""
    container = '$defs' if '$defs' in snapshot_doc else 'definitions'
    shapes: dict[str, dict] = {name: to_house(body) for name, body in snapshot_doc[container].items()}
    for name, body in SYNTHETIC_BASES.items():
        assert name not in shapes, f'upstream now defines {name}; the synthetic base needs a new name'
        shapes[name] = dict(body)
    definitions = {}
    for name, flat in shapes.items():
        bases = composed.get(name, [])
        for b in bases:
            assert b in shapes, f'{name}: declared base {b} is no definition'
            assert refines(shapes[b], flat), (f'{name}: declared base {b} does not hold - the definition '
                                              f'does not refine it (composition.csv row to re-judge)')
        body = _composed(name, flat, bases, shapes)
        text = body.get('description') or described.get(name)
        assert text, f'{name}: no description upstream and none in {DESCRIPTIONS.relative_to(REPO)}'
        body['title'] = name
        body['description'] = text
        definitions[name] = _ordered(body)
    _document_enums(definitions, prov['lineage'])
    ordered = {n: definitions[n] for n in _bfs_order(definitions, ROOT_DEFINITION)}
    return {
        '$schema': DRAFT_04,
        'title': FAMILY,
        'description': (
            'House factoring of the Model Context Protocol schema in draft-04 - the composition '
            "upstream's generator flattens, stated once: JSONRPCHeader (the version pin) and "
            'JSONRPCIdentifiedHeader (header plus id) declared as bases, every base live, each '
            'message allOf its header and its own fields, const spelled as one-element enum. '
            'Derived by corpus-yoga protocol sync from the verbatim snapshot rsc/schema/_reference/mcp '
            f"({prov['lineage']} lineage, upstream commit {prov['commit']}, upstream SHA256 "
            f"{prov['sha256']}); structural reference, upstream's schema.ts at that commit: "
            f"{prov['ts_url']}, transcribed as rsc/schema/protocol/mcpMessage/composition.csv and "
            'verified against the snapshot at derivation. Definitions the snapshot leaves undescribed '
            'take their text from rsc/schema/protocol/mcpMessage/description.csv. One instance is one '
            'JSON-RPC message.'
        ),
        'allOf': [{'$ref': f'#/definitions/{ROOT_DEFINITION}'}],
        'definitions': ordered,
    }


def rendered(doc: dict) -> str:
    return json.dumps(doc, indent=2) + '\n'   # ascii-escaped, as every sibling family


# ── the witness ───────────────────────────────────────────────────────────────

def disagreements(house_doc: dict, snapshot_doc: dict) -> list[str]:
    """Every snapshot definition whose house counterpart, flattened and normalized,
    is not equal to it (normalized) - or is missing. Empty means agreement."""
    container = '$defs' if '$defs' in snapshot_doc else 'definitions'
    house = house_doc.get('definitions', {})
    out = []
    for name, body in snapshot_doc[container].items():
        if name not in house:
            out.append(f'{name}: absent from the factoring')
            continue
        try:
            flat = flattened(house[name], house)
        except (Conflict, AssertionError, KeyError) as e:
            out.append(f'{name}: cannot flatten ({e})')
            continue
        if normalized(flat) != normalized(to_house(body)):
            out.append(f'{name}: flattened factoring differs from the snapshot')
    return out


def current_text() -> str:
    """The factoring as it should read now, from the committed inputs."""
    _, doc = snapshot()
    return rendered(factored(doc, descriptions(), composition(), provenance()))
