#!/usr/bin/env python
"""
mcp_factoring.py - the house factoring of the MCP schema (#562): the composition
upstream's generator flattens, stated once in draft-04, derived from the verbatim
snapshot rsc/reference/mcp and written to rsc/schema/protocol/mcpMessage.

Upstream's schema.json inlines every message's envelope (jsonrpc, id, method,
params) because its TypeScript-to-JSON generator flattens `extends`, and it inlines
every type alias (Cursor, ResultType, EmptyResult, JSONArray, the enum-schema
unions) while still emitting the alias definitions, dead. Two tables restore what
schema.ts states - extracted from the committed schema.ts at every sync by
mcp_extraction.py's rules (#581), written under tmp/cache/mcp/ as their readable
face - and one is house prose beside the family's version; every row is VERIFIED
against the snapshot before it is used, so a row the data does not bear refuses the
derivation rather than misstating the schema:

- composition (definition, base): schema.ts's `extends`, whole, in declaration order. A
  definition is written as allOf [bases..., its own fields]; adding a base's
  constraints to the definition must change nothing (the definition refines it).
  Where the definition instead OVERRIDES a base's property with a conflicting
  shape (SubscriptionsListenResult narrows Result's `_meta` to another $ref) -
  which `extends` permits and allOf cannot express - the definition stands flat
  and the override is a derived fact `overrides()` reports; any other unbearable
  row refuses the derivation. The four JSON-RPC envelope bases are realized by two headers upstream never
  names, JSONRPCHeader (the version pin) and JSONRPCIdentifiedHeader (header plus
  id), because allOf conjoins and cannot narrow the generic envelope's open
  `params` the way `extends` does - the one place the factoring and schema.ts
  diverge, by necessity.
- alias (definition, pointer, alias): where schema.ts uses an alias the generator
  inlined - its snapshot definition referenced by nothing - and where an alias names
  one type the generator copied; the inline subschema at the pointer is replaced by
  a $ref to the alias (a pointer to an anyOf splices the alias's members out and the
  alias in; an empty pointer replaces the whole body), after checking the two
  resolve to the same shape.
- description.csv (name, description): house text for the definitions the
  snapshot leaves undescribed - hand-written, committed beside the version file.
- unreachable.csv (name, reason): the definitions no message carries, hand-written
  beside the version file and read by structure.all_definitions_reachable; the
  derivation refuses a table that disagrees with the wire.

The root is a house definition, MCPMessage: the wire message read as any of the
typed message shapes upstream exports but no definition references (the
direction unions, the typed result responses, the typed error responses), plus
house wrappers giving the result and error unions a party sends their message.
A party's results are carried only when the other party declares requests
(PARTIES): where schema.ts declares no ServerRequest, no message carries a
ClientResult, and no wrapper is minted for one - the union stands unreachable,
declared as such in unreachable.csv. Every other definition is reachable from
the root, and the house diagnostics hold over the family.

The witness is `disagreements()`: every snapshot definition and its house
counterpart - flattened (allOf merged), both resolved through their $refs to a
bounded nesting depth (recursive shapes truncate identically), nested anyOf
spliced, documentation dropped, const as one-element enum, the vacuous
additionalProperties {} dropped, order-free lists sorted - must compare equal.
The dev gate holds it over the committed file.
"""

import csv
import json
import re
import sys
from pathlib import Path

SELF = 'src/main/mcp/mcp_factoring.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))  # src/ - modules both tiers import
from schema_walk import schema_nodes, rebuilt  # noqa: E402  (positions derived from the meta-schema, #571)
sys.path.insert(0, str(REPO / 'src' / 'main'))  # src/main - the tier's shared modules
from latest import latest_file  # noqa: E402
import mcp_extraction as extraction  # noqa: E402  (sibling module)

SNAPSHOT_DIR = REPO / 'rsc/reference/mcp'
PROVENANCE   = SNAPSHOT_DIR / 'provenance.csv'
FAMILY_DIR   = REPO / 'rsc/schema/protocol/mcpMessage'
DESCRIPTIONS = FAMILY_DIR / 'description.csv'
UNREACHABLE  = FAMILY_DIR / 'unreachable.csv'
CACHE_DIR    = REPO / 'tmp/cache/mcp'          # the extracted tables' readable face (rsc/cache_io.csv)
COMPOSITION  = CACHE_DIR / 'composition.csv'
ALIASES      = CACHE_DIR / 'alias.csv'
FAMILY       = 'mcpMessage'
ROOT_DEFINITION = 'MCPMessage'
# The two session roles: a party's results answer the other party's requests.
PARTIES = {'Client': 'Server', 'Server': 'Client'}
DRAFT_04 = 'http://json-schema.org/draft-04/schema#'
RESOLUTION_DEPTH = 12      # nesting levels a recursive shape is expanded to before it is cut

DOCUMENTATION_KEYS = ('title', 'description', '$comment', 'examples')
KEY_ORDER = ('title', 'description', 'type', 'allOf', 'anyOf', 'oneOf', '$ref', 'enum',
             'format', 'pattern', 'minimum', 'maximum', 'minLength', 'maxLength',
             'minItems', 'maxItems', 'items', 'properties', 'required',
             'additionalProperties', 'default')
EXHAUSTIVE_CLAUSE = 'The values are exhaustive: those the MCP {lineage} spec enumerates.'

# The design the factoring adds, beyond what the tables transcribe.
HEADERS = {
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
# An envelope base declared in schema.ts is realized by the header that fits it.
ENVELOPE_BASES = {
    'JSONRPCRequest': 'JSONRPCIdentifiedHeader',
    'JSONRPCNotification': 'JSONRPCHeader',
    'JSONRPCResultResponse': 'JSONRPCIdentifiedHeader',
    'JSONRPCErrorResponse': 'JSONRPCHeader',
}
# The envelopes' own composition: header plus payload base (schema.ts: JSONRPCRequest
# extends Request, JSONRPCNotification extends Notification; the responses have none).
HOUSE_COMPOSITION = {
    'JSONRPCRequest': ['JSONRPCIdentifiedHeader', 'Request'],
    'JSONRPCNotification': ['JSONRPCHeader', 'Notification'],
    'JSONRPCResultResponse': ['JSONRPCIdentifiedHeader'],
    'JSONRPCErrorResponse': ['JSONRPCHeader'],
    'JSONRPCIdentifiedHeader': ['JSONRPCHeader'],
}
RESULT_BASE = 'Result'
ERROR_BASE = 'Error'
HOUSE_DESCRIPTIONS = {
    ROOT_DEFINITION:
        'One MCP message: a JSON-RPC message, read as any of the typed message shapes '
        'upstream exports but no definition references - the direction unions, the typed '
        'result responses, the typed error responses - and as the house wrappers that give '
        'the result and error unions a party sends their message. Every branch is a '
        'JSONRPCMessage, so the union admits exactly what the wire admits.',
    'ProtocolError':
        "The JSON-RPC error objects upstream types by code and no definition references.",
    'ProtocolErrorResponse':
        'An error response whose error is one of the typed protocol errors.',
}
RESULT_RESPONSE_DESCRIPTION = 'A result response whose result is one of {union} - the results {who}.'
RESULT_UNION_WHO = {'ClientResult': 'a client returns', 'ServerResult': 'a server returns'}


# ── inputs ────────────────────────────────────────────────────────────────────

def latest_version(family_dir: Path):
    versions = sorted(family_dir.glob('v*.json'),
                      key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)])
    return versions[-1] if versions else None


def snapshot() -> tuple[Path, dict]:
    path = latest_file(SNAPSHOT_DIR)
    assert path, f'{SNAPSHOT_DIR.relative_to(REPO)} holds no lineage'
    return path, json.loads(path.read_text())


def provenance() -> dict:
    """The snapshot's pinned URL, upstream commit and SHA256, and the schema.ts
    beside it - the rows of the reference project's provenance.csv for the
    lineage held (#572)."""
    path = latest_file(SNAPSHOT_DIR)
    assert path, f'{SNAPSHOT_DIR.relative_to(REPO)} holds no lineage'
    lineage = path.parent.name
    rows = {r['file']: r for r in _rows(PROVENANCE) if r['lineage'] == lineage}
    assert 'schema.json' in rows, f'{PROVENANCE.relative_to(REPO)} pins no schema.json for {lineage}'
    json_row = rows['schema.json']
    ts_row = rows.get('schema.ts')
    ts_url = ts_row['url'].replace('/refs/heads/main/', f"/{ts_row['pin']}/") if ts_row else ''
    return {'url': json_row['url'], 'lineage': lineage, 'commit': json_row['pin'], 'sha256': json_row['sha256'],
            'ts_url': ts_url}


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline='') as fh:
        return list(csv.DictReader(fh))


def schema_ts() -> Path:
    """The committed schema.ts beside the snapshot."""
    path = snapshot()[0].with_name('schema.ts')
    assert path.is_file(), f'{path.relative_to(REPO)} absent - the lineage holds schema.json and schema.ts'
    return path


def declarations():
    return extraction.declarations(schema_ts().read_text())


def composition() -> dict[str, list[str]]:
    """{definition: [base, ...]} as schema.ts declares it (extracted, #581)."""
    return extraction.composition(declarations()[0])


def _dead(shapes: dict) -> set[str]:
    """Definitions nothing in the snapshot references - the aliases the generator
    inlined."""
    referenced = set()
    for body in shapes.values():
        for _, node in schema_nodes(body):
            if isinstance(node.get('$ref'), str):
                referenced.add(node['$ref'].split('/')[-1])
    return set(shapes) - referenced


def _union_index(union: str, alias: str, shapes: dict) -> int:
    """The anyOf member of the snapshot's union that is the alias's shape."""
    ref = {'$ref': f'#/definitions/{alias}'}
    for i, member in enumerate(shapes[union].get('anyOf', [])):
        if _comparable(member, shapes) == _comparable(ref, shapes):
            return i
    raise AssertionError(f'{union}: no anyOf member is {alias}')


def alias_rows(shapes: dict) -> list[tuple[str, str, str]]:
    """(definition, pointer within it, alias), derived from schema.ts (#581): a copy
    site for every alias naming one type; a use site for every alias the generator
    inlined - a property typed by it, or a union alias listing it (spliced when the
    alias is itself a union, else the member holding its shape)."""
    interfaces, aliases = declarations()
    dead = _dead(shapes)
    by_name = {a.name: a for a in aliases}
    rows: list[tuple[str, str, str]] = []
    for a in aliases:
        if a.single and a.single in shapes and a.name in shapes:
            rows.append((a.name, '', a.single))
    for a in aliases:
        if a.name not in dead or a.name not in shapes:
            continue
        for interface, pointer in extraction.property_sites(interfaces, a.name):
            if interface in shapes:
                rows.append((interface, pointer, a.name))
        for union in extraction.union_sites(aliases, a.name):
            if union not in shapes or by_name[union].single:
                continue
            pointer = 'anyOf' if a.union else f'anyOf/{_union_index(union, a.name, shapes)}'
            rows.append((union, pointer, a.name))
    return rows


def written_tables(declared: dict, rows: list) -> list[Path]:
    """Write the two extracted tables under tmp/cache/mcp/ (QUOTE_ALL, as every
    sibling table) - the readable face of the derivation's inputs."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with COMPOSITION.open('w', newline='') as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(['definition', 'base'])
        for name, bases in declared.items():
            for b in bases:
                w.writerow([name, b])
    with ALIASES.open('w', newline='') as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(['definition', 'pointer', 'alias'])
        w.writerows(rows)
    return [COMPOSITION, ALIASES]


def descriptions() -> dict:
    return {row['name']: row['description'] for row in _rows(DESCRIPTIONS)}


def unreachable() -> dict:
    return {row['name']: row['reason'] for row in _rows(UNREACHABLE)}


def uncarried_results(shapes: dict) -> list[tuple[str, str]]:
    """(result union, the request union whose absence leaves it uncarried): a party's
    result union when the snapshot declares no request union for the other party -
    no message carries such a result."""
    return [(f'{party}Result', f'{other}Request') for party, other in PARTIES.items()
            if f'{party}Result' in shapes and f'{other}Request' not in shapes]


# ── schema algebra ────────────────────────────────────────────────────────────

def _mapped(node: dict, keywords) -> dict:
    """node with `keywords` applied at every schema position - a shallow rewrite of
    one schema dict's keys - descending only into schema positions as the
    meta-schema declares them (schema_walk), so a property named const, enum or
    $ref is a name, never a keyword."""
    return rebuilt(keywords(node), lambda child: _mapped(child, keywords))


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


def resolved(node: dict, definitions: dict, depth: int = 0) -> dict:
    """node with every $ref replaced by its target (allOf flattened, siblings
    conjoined), nested anyOf spliced, to RESOLUTION_DEPTH nesting levels - beyond
    which a schema position is cut to {} so recursive shapes truncate identically
    however many alias hops they take."""
    if depth > RESOLUTION_DEPTH:
        return {}
    node = flattened(node, definitions)
    if isinstance(node.get('$ref'), str):
        name = node['$ref'].split('/')[-1]
        target = definitions.get(name)
        if isinstance(target, dict):
            rest = {k: v for k, v in node.items() if k != '$ref'}
            return resolved(merged(dict(target), rest), definitions, depth)
    if isinstance(node.get('anyOf'), list):
        node = {**node, 'anyOf': _spliced(node['anyOf'], definitions)}
    return rebuilt(node, lambda child: resolved(child, definitions, depth + 1))


def _spliced(members: list, definitions: dict) -> list:
    """An anyOf's members with every member that is itself a bare anyOf - directly,
    or through a chain of $ref aliases - replaced by its own members, recursively,
    BEFORE descent: a spliced member sits at the same nesting depth as its
    siblings, so an alias to a union costs no depth against the inline form."""
    out = []
    for m in members:
        mm = flattened(m, definitions) if isinstance(m, dict) else m
        while isinstance(mm, dict) and isinstance(mm.get('$ref'), str):
            target = definitions.get(mm['$ref'].split('/')[-1])
            if not isinstance(target, dict):
                break
            mm = flattened(merged(dict(target), {k: v for k, v in mm.items() if k != '$ref'}), definitions)
        if isinstance(mm, dict) and set(mm) - set(DOCUMENTATION_KEYS) == {'anyOf'}:
            out += _spliced(mm['anyOf'], definitions)
        else:
            out.append(mm)
    return out


def _comparable(node: dict, definitions: dict) -> str:
    """The witness's canonical text of a definition: resolved, normalized, sorted."""
    return json.dumps(normalized(resolved(node, definitions)), sort_keys=True)


# ── the factoring ─────────────────────────────────────────────────────────────

def _ordered(defn: dict) -> dict:
    rank = {k: i for i, k in enumerate(KEY_ORDER)}
    return {k: defn[k] for k in sorted(defn, key=lambda k: (rank.get(k, len(KEY_ORDER)), k))}


def _composed(flat: dict, bases: list[str], shapes: dict) -> dict:
    """flat, rewritten as allOf [bases..., own fields]: a property a base supplies
    identically is omitted, a property the definition refines or adds stays, and
    `required` keeps what no base requires (with its property, so it names only
    local properties)."""
    if not bases:
        return dict(flat)
    supplied_props: dict = {}
    supplied_required: list = []
    for b in bases:
        supplied_props.update(shapes[b].get('properties', {}))
        supplied_required += shapes[b].get('required', [])
    own = {k: v for k, v in flat.items() if k not in ('properties', 'required')}
    required = [r for r in flat.get('required', []) if r not in supplied_required]
    props = {p: s for p, s in flat.get('properties', {}).items()
             if p not in supplied_props or normalized(supplied_props[p]) != normalized(s)
             or p in required}
    own['allOf'] = [{'$ref': f'#/definitions/{b}'} for b in bases]
    if props:
        own['properties'] = props
    if required:
        own['required'] = required
    return own


def _bearing(name: str, base: str, shapes: dict) -> str:
    """'holds' when the definition refines the base; 'override' when a shared
    property conflicts (a TS override allOf cannot express); 'unbearable' otherwise -
    the base says something the definition does not, a transcription to re-judge."""
    flat = shapes[name]
    try:
        return 'holds' if normalized(merged(shapes[base], flat)) == normalized(flat) else 'unbearable'
    except Conflict:
        return 'override'


def overrides(shapes: dict, declared: dict) -> list[tuple[str, str]]:
    """(definition, base) rows schema.ts declares that the definition overrides."""
    return [(n, ENVELOPE_BASES.get(b, b)) for n in shapes for b in _realized_bases(n, declared)
            if b in shapes and _bearing(n, b, shapes) == 'override']


def _realized_bases(name: str, declared: dict) -> list[str]:
    """The bases a definition is composed over: the house envelopes' own, else the
    declared schema.ts bases with envelope bases realized by their headers."""
    if name in HOUSE_COMPOSITION:
        return HOUSE_COMPOSITION[name]
    out = []
    for b in declared.get(name, []):
        b = ENVELOPE_BASES.get(b, b)
        if b not in out:
            out.append(b)
    return sorted(out)


def _descends_from(name: str, ancestor: str, declared: dict, _seen=()) -> bool:
    if name == ancestor:
        return True
    if name in _seen:
        return False
    return any(_descends_from(b, ancestor, declared, _seen + (name,)) for b in declared.get(name, []))


def _union_members(defn: dict) -> list[str] | None:
    """The member names of a bare anyOf union (documentation aside), else None."""
    if set(defn) - set(DOCUMENTATION_KEYS) != {'anyOf'}:
        return None
    names = [m['$ref'].split('/')[-1] for m in defn['anyOf'] if isinstance(m.get('$ref'), str)]
    return names if len(names) == len(defn['anyOf']) else None


def _classify(shapes: dict, declared: dict) -> dict[str, str]:
    """{name: 'message' | 'result' | 'error' | ''}: a definition's kind by its declared
    lineage - an envelope, or a descendant of one, is a message; a descendant of
    Result a result; of Error an error object; a bare alias its target's kind; a bare
    union its members' kind when they agree. `shapes` are the bodies as written
    (aliases revived), so an alias upstream inlined as a copy classifies by its target."""
    kinds: dict[str, str] = {}
    def kind(name, _seen=()):
        if name in kinds:
            return kinds[name]
        if name in _seen:
            return ''
        k = ''
        if name in ENVELOPE_BASES or name in ('JSONRPCMessage', 'JSONRPCResponse'):
            k = 'message'
        elif any(_descends_from(name, e, declared) for e in ENVELOPE_BASES):
            k = 'message'
        elif _descends_from(name, RESULT_BASE, declared):
            k = 'result'
        elif _descends_from(name, ERROR_BASE, declared):
            k = 'error'
        elif name in shapes and set(shapes[name]) - set(DOCUMENTATION_KEYS) == {'$ref'}:
            k = kind(shapes[name]['$ref'].split('/')[-1], _seen + (name,))   # a bare alias: its target's kind
        else:
            members = _union_members(shapes[name]) if name in shapes else None
            if members:
                member_kinds = {kind(m, _seen + (name,)) for m in members if m in shapes}
                if len(member_kinds) == 1:
                    k = member_kinds.pop()
        kinds[name] = k
        return k
    for name in shapes:
        kind(name)
    return kinds


def _referenced(definitions: dict) -> set[str]:
    out = set()
    for defn in definitions.values():
        for _, node in schema_nodes(defn):
            if isinstance(node.get('$ref'), str):
                out.add(node['$ref'].split('/')[-1])
    return out


def _house_root(definitions: dict, shapes: dict, declared: dict) -> dict:
    """MCPMessage and its wrappers: every message-shaped definition nothing references
    is a branch; an unreferenced result union a party sends gets a <Union>Response
    wrapper (a party's results are sent only when the other party declares
    requests - uncarried_results); the unreferenced error objects gather in
    ProtocolError under ProtocolErrorResponse."""
    kinds = _classify(definitions, declared)
    referenced = _referenced(definitions)
    uncarried = {union for union, _ in uncarried_results(shapes)}
    loose = [n for n in shapes if n not in referenced and n not in HEADERS]
    branches = [n for n in loose if kinds[n] == 'message']
    for union in [n for n in loose if kinds[n] == 'result' and n not in uncarried]:
        wrapper = f'{union}Response'
        assert wrapper not in shapes, f'upstream now defines {wrapper}; the house wrapper needs a new name'
        definitions[wrapper] = _ordered({
            'title': wrapper,
            'description': RESULT_RESPONSE_DESCRIPTION.format(union=union, who=RESULT_UNION_WHO.get(union, 'of that union')),
            'type': 'object',
            'allOf': [{'$ref': '#/definitions/JSONRPCIdentifiedHeader'}],
            'properties': {'result': {'$ref': f'#/definitions/{union}'}},
            'required': ['result'],
        })
        branches.append(wrapper)
    errors = [n for n in loose if kinds[n] == 'error']
    if errors:
        for n in ('ProtocolError', 'ProtocolErrorResponse'):
            assert n not in shapes, f'upstream now defines {n}; the house definition needs a new name'
        definitions['ProtocolError'] = _ordered({
            'title': 'ProtocolError', 'description': HOUSE_DESCRIPTIONS['ProtocolError'],
            'anyOf': [{'$ref': f'#/definitions/{n}'} for n in errors]})
        definitions['ProtocolErrorResponse'] = _ordered({
            'title': 'ProtocolErrorResponse', 'description': HOUSE_DESCRIPTIONS['ProtocolErrorResponse'],
            'type': 'object',
            'allOf': [{'$ref': '#/definitions/JSONRPCHeader'}],
            'properties': {'id': {'$ref': '#/definitions/RequestId'}, 'error': {'$ref': '#/definitions/ProtocolError'}},
            'required': ['error']})
        branches.append('ProtocolErrorResponse')
    assert ROOT_DEFINITION not in shapes, f'upstream now defines {ROOT_DEFINITION}; the house root needs a new name'
    return _ordered({'title': ROOT_DEFINITION, 'description': HOUSE_DESCRIPTIONS[ROOT_DEFINITION],
                     'anyOf': [{'$ref': f'#/definitions/{n}'} for n in branches]})


def _apply_alias(definitions: dict, name: str, pointer: str, alias: str, shapes: dict) -> None:
    """Replace the subschema at pointer (within definitions[name]) by a $ref to alias -
    or, when the pointer names an anyOf, splice the alias's members out and the alias
    in - after checking the replaced material and the alias resolve to one shape."""
    assert alias in shapes, f'{name}: alias {alias} is no definition'
    defn = definitions[name]
    alias_ref = {'$ref': f'#/definitions/{alias}'}
    if pointer == '':
        before = {k: v for k, v in defn.items() if k not in DOCUMENTATION_KEYS}
        assert _comparable(before, shapes) == _comparable(alias_ref, shapes), f'{name}: does not resolve to alias {alias}'
        for k in list(defn):
            if k not in DOCUMENTATION_KEYS:
                del defn[k]
        defn.update(alias_ref)
        return
    tokens = pointer.split('/')
    parent = defn
    for tok in tokens[:-1]:
        parent = parent[int(tok)] if isinstance(parent, list) else parent[tok]
    last = tokens[-1]
    if last == 'anyOf' and isinstance(parent.get('anyOf'), list):
        alias_members = _union_members(shapes[alias]) or []
        resolved_alias = resolved(alias_ref, shapes)
        wanted = {json.dumps(normalized(m), sort_keys=True) for m in resolved_alias.get('anyOf', [])}
        keep, removed, inserted = [], 0, False
        for m in parent['anyOf']:
            if json.dumps(normalized(resolved(m, shapes)), sort_keys=True) in wanted:
                removed += 1
                if not inserted:
                    keep.append(alias_ref)
                    inserted = True
            else:
                keep.append(m)
        assert removed == len(wanted) and removed > 0, (f'{name}/{pointer}: the anyOf does not carry exactly the members '
                                                          f'of {alias} ({removed} of {len(wanted)} found)')
        parent['anyOf'] = keep
        return
    target = parent[int(last)] if isinstance(parent, list) else parent[last]
    assert _comparable(target, shapes) == _comparable(alias_ref, shapes), f'{name}/{pointer}: does not resolve to alias {alias}'
    docs = {k: v for k, v in target.items() if k in DOCUMENTATION_KEYS}
    replacement = {**alias_ref, **docs}
    if isinstance(parent, list):
        parent[int(last)] = replacement
    else:
        parent[last] = replacement


def _document_enums(definitions: dict, lineage: str) -> None:
    clause = EXHAUSTIVE_CLAUSE.format(lineage=lineage)
    for defn in definitions.values():
        for _, node in schema_nodes(defn):
            if isinstance(node.get('enum'), list) and len(node['enum']) > 1:
                text = node.get('description', '')
                if not any(w in text.lower() for w in ('exhaustive', 'open set', 'discriminator')):
                    node['description'] = (text + ' ' + clause).strip()


def _reached(definitions: dict, root: str) -> list[str]:
    """Breadth-first referential encounter order from root - the definitions the
    root reaches."""
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
    return order


def _bfs_order(definitions: dict, root: str) -> list[str]:
    """The reached order, the unreachable after, alphabetical - the order
    structure.bfs_order asks of every house schema."""
    order = _reached(definitions, root)
    return order + sorted(n for n in definitions if n not in order)


def factored(snapshot_doc: dict, described: dict, declared: dict, alias_rows: list, prov: dict,
             undelivered: dict) -> dict:
    """The house schema, whole: every snapshot definition composed over its declared
    bases (each verified to hold), the headers, the aliases revived, the house root
    and its wrappers, titles and descriptions per house rule, definitions in BFS
    order from the root. `undelivered` is unreachable.csv: it must name exactly the
    definitions the root does not reach, or the derivation refuses."""
    container = '$defs' if '$defs' in snapshot_doc else 'definitions'
    shapes: dict[str, dict] = {name: to_house(body) for name, body in snapshot_doc[container].items()}
    for name, body in HEADERS.items():
        assert name not in shapes, f'upstream now defines {name}; the header needs a new name'
        shapes[name] = dict(body)
    definitions = {}
    for name, flat in shapes.items():
        bases = []
        for b in _realized_bases(name, declared):
            assert b in shapes, f'{name}: declared base {b} is no definition'
            bearing = _bearing(name, b, shapes)
            assert bearing != 'unbearable', (f'{name}: declared base {b} says something the definition '
                                             f'does not (composition row schema.ts states; the extraction rule to re-judge)')
            if bearing == 'holds':
                bases.append(b)
        body = _composed(flat, bases, shapes)
        text = body.get('description') or described.get(name)
        assert text, f'{name}: no description upstream and none in {DESCRIPTIONS.relative_to(REPO)}'
        body['title'] = name
        body['description'] = text
        definitions[name] = body
    for name, pointer, alias in alias_rows:
        assert name in definitions, f'alias row names no definition: {name}'
        _apply_alias(definitions, name, pointer, alias, shapes)
    definitions[ROOT_DEFINITION] = _house_root(definitions, shapes, declared)
    definitions = {n: _ordered(d) for n, d in definitions.items()}
    _document_enums(definitions, prov['lineage'])
    order = _bfs_order(definitions, ROOT_DEFINITION)
    reached = set(_reached(definitions, ROOT_DEFINITION))
    for union, request in uncarried_results(shapes):
        assert union in undelivered, (f'{union}: no message carries it ({request} is not declared in schema.ts) - '
                                      f'declare it in {UNREACHABLE.relative_to(REPO)}')
    for name in undelivered:
        assert name in definitions, f'{UNREACHABLE.relative_to(REPO)} names no definition: {name}'
        assert name not in reached, f'{UNREACHABLE.relative_to(REPO)} declares {name} unreachable, but {ROOT_DEFINITION} reaches it'
    unexplained = [n for n in definitions if n not in reached and n not in undelivered]
    assert not unexplained, f'{ROOT_DEFINITION} does not reach {unexplained} and {UNREACHABLE.relative_to(REPO)} does not declare them'
    ordered = {n: definitions[n] for n in order}
    return {
        '$schema': DRAFT_04,
        'title': FAMILY,
        'description': (
            'House factoring of the Model Context Protocol schema in draft-04 - the composition '
            "upstream's generator flattens, stated once: JSONRPCHeader (the version pin) and "
            'JSONRPCIdentifiedHeader (header plus id) declared as bases, every base live, each '
            'message allOf its header and its own fields, the type aliases upstream inlined '
            'revived as refs, const spelled as one-element enum, and MCPMessage the root - the '
            'wire message read as any typed message shape upstream exports. Derived by '
            'corpus-yoga mcp sync from the verbatim snapshot rsc/reference/mcp '
            f"({prov['lineage']} lineage, upstream commit {prov['commit']}, upstream SHA256 "
            f"{prov['sha256']}) and from upstream's schema.ts at that commit beside it ({prov['ts_url']}), "
            'whose extends clauses and type aliases src/main/mcp/mcp_extraction.py reads by stated rules, every '
            'row verified against the snapshot at derivation. Definitions the snapshot leaves undescribed take their text from '
            'rsc/schema/protocol/mcpMessage/description.csv; the definitions no message carries are declared in '
            'rsc/schema/protocol/mcpMessage/unreachable.csv. One instance is one JSON-RPC message.'
        ),
        'allOf': [{'$ref': f'#/definitions/{ROOT_DEFINITION}'}],
        'definitions': ordered,
    }


def rendered(doc: dict) -> str:
    return json.dumps(doc, indent=2) + '\n'   # ascii-escaped, as every sibling family


# ── the witness ───────────────────────────────────────────────────────────────

def disagreements(house_doc: dict, snapshot_doc: dict) -> list[str]:
    """Every snapshot definition whose house counterpart, resolved and normalized, is
    not equal to it (resolved and normalized in its own document) - or is missing.
    Empty means agreement."""
    container = '$defs' if '$defs' in snapshot_doc else 'definitions'
    house = house_doc.get('definitions', {})
    snap = {name: to_house(body) for name, body in snapshot_doc[container].items()}
    out = []
    for name, body in snap.items():
        if name not in house:
            out.append(f'{name}: absent from the factoring')
            continue
        try:
            if _comparable(house[name], house) != _comparable(body, snap):
                out.append(f'{name}: resolved factoring differs from the snapshot')
        except (Conflict, AssertionError, KeyError) as e:
            out.append(f'{name}: cannot resolve ({e})')
    return out


def shapes_and_declared() -> tuple[dict, dict]:
    """The flat house-dialect shapes (snapshot plus headers) and the extracted
    composition - what status reports overrides from."""
    _, doc = snapshot()
    container = '$defs' if '$defs' in doc else 'definitions'
    shapes = {name: to_house(body) for name, body in doc[container].items()}
    shapes.update({n: dict(b) for n, b in HEADERS.items()})
    return shapes, composition()


def inputs() -> tuple[dict, dict, list]:
    """(shapes, composition, alias rows) - the derivation's inputs as extracted now."""
    shapes, declared = shapes_and_declared()
    return shapes, declared, alias_rows(shapes)


def current_text() -> str:
    """The factoring as it should read now, from the committed inputs."""
    _, doc = snapshot()
    shapes, declared, rows = inputs()
    return rendered(factored(doc, descriptions(), declared, rows, provenance(), unreachable()))
