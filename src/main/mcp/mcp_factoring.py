#!/usr/bin/env python
"""
mcp_factoring.py - the house factoring of the MCP schema (#562, #598): generated from
upstream's schema.ts alone, in draft-04, and written to rsc/schema/protocol/mcpMessage;
upstream's schema.json stands as the witness the result must flatten to, never as a
source.

mcp_generation.py reads schema.ts through the house TypeScript grammar into the flat
shape of every exported interface and alias - the shape upstream's generator would
flatten it to, one stated rule per TypeScript form. This module composes those
shapes over the bases schema.ts declares, and adds what the house adds:

- composition (definition, base): schema.ts's `extends`, whole, in declaration order
  (mcp_extraction, faced under tmp/cache/mcp/). A definition is written as allOf
  [bases..., its own fields]; adding a base's constraints to the definition must
  change nothing (the definition refines it). Where the definition instead
  OVERRIDES a base's property with a conflicting shape (SubscriptionsListenResult
  narrows Result's `_meta` to another $ref) - which `extends` permits and allOf
  cannot express - the definition stands flat and the override is a derived fact
  `overrides()` reports. The four JSON-RPC envelope bases are realized by two headers
  upstream never names, JSONRPCHeader (the version pin) and JSONRPCIdentifiedHeader
  (header plus id), because allOf conjoins and cannot narrow the generic envelope's
  open `params` the way `extends` does - the one place the factoring and schema.ts
  diverge, by necessity.
- category (definition, category): the @category tag schema.ts carries on a
  declaration, faced beside the composition (#595).
- description.csv (name, description): house text for the definitions schema.ts
  leaves without a JSDoc - hand-written, committed beside the version file.
- unreachable.csv (name, reason): the definitions no message carries, hand-written
  beside the version file and read by structure.all_definitions_reachable; the
  derivation refuses a table that disagrees with the wire.
- layer.csv (layer, reading): the layers the protocol reads by, one row each -
  the closed vocabulary every rule and placement row draws on; hand-written
  beside the version file.
- category_layer.csv (category, layer): the house's reading of upstream's
  categories - a method tag by its first path segment, a named tag as itself - into
  those layers; hand-written beside the version file. A definition the tag
  places, the alias target, the union members or the descendants place (when they
  agree), else placement.csv (lineage, definition, layer, reason) places by hand;
  a definition none of these place refuses the derivation, and a placement row for a
  definition the rule already places refuses too. Every definition's description
  ends with its layer, so the version file reads by concern.
- addition.csv (definition, pointer, upstream, house): where the house schema reads
  differently from upstream's at a JSON Pointer - what upstream's generator drops
  (JSONValue's null) and what the house adds beyond schema.ts (the protocol version
  pinned on the `_meta` field that names it, `${LATEST_PROTOCOL_VERSION}` read from
  the constant). The derivation applies a row whose upstream reading it generated
  and refuses a row that fits neither reading; the witness sets each row's house
  reading back to upstream's before comparing, and refuses a row upstream no longer
  bears.

The root is a house definition, MCPMessage: the wire message read as any of the
typed message shapes upstream exports but no definition references (the
direction unions, the typed result responses, the typed error responses), plus
house wrappers giving the result and error unions a party sends their message.
A party's results are carried only when the other party declares requests
(PARTIES): where schema.ts declares no ServerRequest, no message carries a
ClientResult, and no wrapper is minted for one - the union stands unreachable,
declared as such in unreachable.csv. Every other definition is reachable from
the root, and the house diagnostics hold over the family. Every alias schema.ts
declares is a reference wherever it is used: the aliases upstream's generator
inlines and leaves dead are live here by construction.

The witness is `disagreements()`: every snapshot definition and its house
counterpart - flattened (allOf merged), both resolved through their $refs to a
bounded nesting depth (recursive shapes truncate identically), nested anyOf
spliced and order-free, documentation dropped, const as one-element enum, the
vacuous additionalProperties {} and an empty properties map dropped, order-free
lists sorted, the declared additions set back - must compare equal. The dev gate
holds it over the committed file.
"""

import csv
import json
from typing import Any
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
import mcp_generation as generation  # noqa: E402  (sibling module)

SNAPSHOT_DIR = REPO / 'rsc/reference/mcp'
PROVENANCE   = SNAPSHOT_DIR / 'provenance.csv'
FAMILY_DIR   = REPO / 'rsc/schema/protocol/mcpMessage'
DESCRIPTIONS = FAMILY_DIR / 'description.csv'
LAYERS       = FAMILY_DIR / 'layer.csv'
LAYER_RULE   = FAMILY_DIR / 'category_layer.csv'
PLACEMENT    = FAMILY_DIR / 'placement.csv'
UNREACHABLE  = FAMILY_DIR / 'unreachable.csv'
ADDITION     = FAMILY_DIR / 'addition.csv'
CACHE_DIR    = REPO / 'tmp/cache/mcp'          # the extracted tables' readable face (rsc/cache_io.csv)
COMPOSITION  = CACHE_DIR / 'composition.csv'
CATEGORIES   = CACHE_DIR / 'category.csv'
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
LAYER_CLAUSE = 'Layer: {layer}.'

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


_generation: dict[str, generation.Generation] = {}


def generated() -> generation.Generation:
    """schema.ts read whole by the generation, once per text."""
    text = schema_ts().read_text()
    if text not in _generation:
        _generation.clear()
        _generation[text] = generation.Generation(text)
    return _generation[text]


def additions() -> list[dict]:
    return _rows(ADDITION)


ABSENT = object()      # a reading addition.csv leaves blank: the keyword is not there


def _at(node: Any, pointer: str) -> Any:
    """The value at a JSON Pointer within node, ABSENT where the last step finds no key."""
    tokens = pointer.split('/') if pointer else []
    for i, token in enumerate(tokens):
        token = token.replace('~1', '/').replace('~0', '~')
        try:
            node = node[int(token)] if isinstance(node, list) else node[token]
        except (KeyError, IndexError, ValueError):
            if i == len(tokens) - 1:
                return ABSENT
            raise
    return node


def _set(node: Any, pointer: str, value: Any) -> None:
    """Set (or, for ABSENT, remove) the value at a JSON Pointer within node."""
    tokens = pointer.split('/')
    parent = _at(node, '/'.join(tokens[:-1]))
    last = tokens[-1].replace('~1', '/').replace('~0', '~')
    if isinstance(parent, list):
        parent[int(last)] = value
    elif value is ABSENT:
        parent.pop(last, None)
    else:
        parent[last] = value


def _reading(text: str, constants: dict) -> Any:
    """A row's reading as JSON - blank is ABSENT, `${NAME}` the constant's literal."""
    if not text.strip():
        return ABSENT
    for name, value in constants.items():
        text = text.replace('${' + name + '}', json.loads(value) if value.startswith('"') else value)
    return json.loads(text)


def _added(shapes: dict, rows: list[dict], constants: dict) -> None:
    """Apply addition.csv to the generated shapes: at each row's pointer, upstream's
    reading becomes the house's; the house's reading already there is left; any
    other reading refuses the row as stale."""
    for row in rows:
        name, pointer = row['definition'], row['pointer']
        assert name in shapes, f'{ADDITION.relative_to(REPO)} names no definition: {name}'
        upstream, house = _reading(row['upstream'], constants), _reading(row['house'], constants)
        try:
            found = _at(shapes[name], pointer)
        except (KeyError, IndexError, ValueError):
            raise AssertionError(f'{ADDITION.relative_to(REPO)}: {name} has nothing on the way to {pointer!r} - the row is stale')
        if found == upstream or (found is ABSENT and upstream is ABSENT):
            _set(shapes[name], pointer, house)
        else:
            assert found == house, (f'{ADDITION.relative_to(REPO)}: {name} at {pointer!r} reads '
                                    f'{"nothing" if found is ABSENT else json.dumps(found)}, neither the upstream reading '
                                    f'{"nothing" if upstream is ABSENT else json.dumps(upstream)} nor the house reading {json.dumps(house)} - the row is stale')


def categories() -> dict[str, str | None]:
    """{definition: @category tag or None} from the committed schema.ts."""
    return extraction.categories(schema_ts().read_text())


def layer_readings() -> dict[str, str]:
    return {row['layer']: row['reading'] for row in _rows(LAYERS)}


def layer_rule() -> dict[str, str]:
    return {row['category']: row['layer'] for row in _rows(LAYER_RULE)}


def placements(lineage: str) -> dict[str, dict]:
    """{definition: row} of placement.csv for this lineage (a blank lineage is every lineage)."""
    return {row['definition']: row for row in _rows(PLACEMENT) if row['lineage'] in ('', lineage)}


def concern(category: str) -> str:
    """A method tag names its first path segment; a named tag names itself."""
    return category.split('/')[0] if '/' in category else category


def layers(definitions: dict, tagged: dict, rule: dict, placed: dict, declared: dict) -> dict[str, str]:
    """{definition: layer}: a tagged definition by layer.csv's row for its concern; an
    untagged one by its alias target, its union members or its descendants when they
    agree; the residue by placement.csv; anything else refuses. A placement for a
    definition the rule places refuses as a restatement."""
    known = set(layer_readings())
    assert known, f'{LAYERS.relative_to(REPO)} names no layer'
    unknown = sorted({(c, l) for c, l in rule.items() if l not in known})
    assert not unknown, f'{LAYER_RULE.relative_to(REPO)} names a layer {LAYERS.relative_to(REPO)} does not: {unknown}'
    layer: dict[str, str] = {}
    for name in definitions:
        tag = tagged.get(name)
        if tag is not None:
            key = concern(tag)
            assert key in rule, f'{name}: schema.ts tags it {tag!r} and {LAYER_RULE.relative_to(REPO)} has no row for {key!r}'
            layer[name] = rule[key]
    children: dict[str, set] = {}
    for name, bases in declared.items():
        for b in bases:
            children.setdefault(b, set()).add(name)
    def candidates(name):
        body = definitions[name]
        if isinstance(body.get('$ref'), str):
            return [body['$ref'].split('/')[-1]]
        if isinstance(body.get('anyOf'), list) and all(isinstance(m.get('$ref'), str) for m in body['anyOf']):
            return [m['$ref'].split('/')[-1] for m in body['anyOf']]
        return sorted(children.get(name, ()))
    changed = True
    while changed:
        changed = False
        for name in definitions:
            if name in layer:
                continue
            found = [c for c in candidates(name) if c in definitions]
            if found and all(c in layer for c in found) and len({layer[c] for c in found}) == 1:
                layer[name] = layer[found[0]]
                changed = True
    for name, row in placed.items():
        assert name in definitions, f'{PLACEMENT.relative_to(REPO)} places {name}, which is no definition'
        assert name not in layer, (f'{PLACEMENT.relative_to(REPO)} places {name}, which the rule already places '
                                   f'({layer.get(name)}) - the row restates')
        layer[name] = row['layer']
    residue = [n for n in definitions if n not in layer]
    assert not residue, (f'no layer for {residue}: schema.ts tags none of them, their targets, members or '
                         f'descendants disagree or are unplaced, and {PLACEMENT.relative_to(REPO)} places none - '
                         'place each with its reason')
    strange = sorted({(n, l) for n, l in layer.items() if l not in known})
    assert not strange, f'{PLACEMENT.relative_to(REPO)} names a layer {LAYERS.relative_to(REPO)} does not: {strange}'
    return layer


def partition(doc: dict) -> dict[str, int]:
    """{layer: count} read back from a version file's descriptions - the clause every
    definition ends with."""
    counts: dict[str, int] = {}
    for body in doc.get('definitions', {}).values():
        m = re.search(r'Layer: (\w+)\.$', body.get('description', ''))
        if m:
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def composition() -> dict[str, list[str]]:
    """{definition: [base, ...]} as schema.ts declares it (extracted, #581)."""
    return extraction.composition(declarations()[0])


def written_tables(declared: dict, tagged: dict) -> list[Path]:
    """Write the two extracted tables under tmp/cache/mcp/ (QUOTE_ALL, as every
    sibling table) - the readable face of the derivation's inputs; a stale alias.csv
    from before #598 is removed."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with CATEGORIES.open('w', newline='') as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(['definition', 'category'])
        for name, tag in tagged.items():
            w.writerow([name, tag or ''])
    with COMPOSITION.open('w', newline='') as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(['definition', 'base'])
        for name, bases in declared.items():
            for b in bases:
                w.writerow([name, b])
    (CACHE_DIR / 'alias.csv').unlink(missing_ok=True)
    return [CATEGORIES, COMPOSITION]


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
        if key == 'properties' and value == {}:
            continue
        if key == 'anyOf' and isinstance(value, list):
            value = sorted(value, key=lambda m: json.dumps(m, sort_keys=True))
        if key == '$ref' and isinstance(value, str):
            out[key] = value.split('/')[-1]
            continue
        if key in ('enum', 'required') and isinstance(value, list):
            value = sorted(value, key=json.dumps)
        out[key] = value
    return out


def normalized(node: dict) -> dict:
    """The comparison form: documentation dropped, const as enum, the vacuous
    additionalProperties {} and empty properties dropped, refs by definition name,
    order-free lists (enum, required, anyOf) sorted - two spellings of one
    constraint compare equal, and only keywords are rewritten, never a property
    that shares a keyword's name. Children first, so a sorted list sorts its
    members in their normal form."""
    return _normal_keywords(rebuilt(node, normalized))


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


def factored(flat_shapes: dict, described: dict, declared: dict, prov: dict,
             declared_unreachable: dict, tagged: dict, rule: dict, placed: dict,
             addition_rows: list[dict], constants: dict) -> dict:
    """The house schema, whole: every definition schema.ts declares, generated flat
    and composed over its declared bases (each verified to hold), the headers, the
    additions applied, the house root and its wrappers, titles and descriptions per
    house rule, definitions in BFS order from the root. `declared_unreachable` is
    unreachable.csv: it must name exactly the definitions the root does not reach, or
    the derivation refuses."""
    shapes: dict[str, dict] = json.loads(json.dumps({n: b for n, b in flat_shapes.items() if n not in HEADERS}))
    _added(shapes, addition_rows, constants)
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
        assert text, f'{name}: no JSDoc in schema.ts and no row in {DESCRIPTIONS.relative_to(REPO)}'
        body['title'] = name
        body['description'] = text
        definitions[name] = body
    definitions[ROOT_DEFINITION] = _house_root(definitions, shapes, declared)
    definitions = {n: _ordered(d) for n, d in definitions.items()}
    _document_enums(definitions, prov['lineage'])
    order = _bfs_order(definitions, ROOT_DEFINITION)
    reached = set(_reached(definitions, ROOT_DEFINITION))
    for union, request in uncarried_results(shapes):
        assert union in declared_unreachable, (f'{union}: no message carries it ({request} is not declared in schema.ts) - '
                                      f'declare it in {UNREACHABLE.relative_to(REPO)}')
    for name in declared_unreachable:
        assert name in definitions, f'{UNREACHABLE.relative_to(REPO)} names no definition: {name}'
        assert name not in reached, f'{UNREACHABLE.relative_to(REPO)} declares {name} unreachable, but {ROOT_DEFINITION} reaches it'
    unexplained = [n for n in definitions if n not in reached and n not in declared_unreachable]
    assert not unexplained, f'{ROOT_DEFINITION} does not reach {unexplained} and {UNREACHABLE.relative_to(REPO)} does not declare them'
    layer = layers(definitions, tagged, rule, placed, declared)
    for name, body in definitions.items():
        body['description'] = body['description'].rstrip() + ' ' + LAYER_CLAUSE.format(layer=layer[name])
    ordered = {n: definitions[n] for n in order}
    return {
        '$schema': DRAFT_04,
        'title': FAMILY,
        'description': (
            "House factoring of the Model Context Protocol schema in draft-04, generated from upstream's "
            'schema.ts alone - the composition its generator flattens, stated once: JSONRPCHeader (the '
            'version pin) and JSONRPCIdentifiedHeader (header plus id) declared as bases, every base live, each '
            'message allOf its header and its own fields, every type alias a reference wherever it is used, '
            'const spelled as one-element enum, and MCPMessage the root - the '
            'wire message read as any typed message shape upstream exports. Generated by '
            f"corpus-yoga mcp sync from rsc/reference/mcp/{prov['lineage']}/schema.ts (upstream commit {prov['commit']}, "
            f"{prov['ts_url']}), read through the house TypeScript grammar by src/main/mcp/mcp_generation.py, one stated "
            "rule per TypeScript form; upstream's schema.json at that commit "
            f"(SHA256 {prov['sha256']}) is the witness every definition here must flatten to, up to the readings "
            'rsc/schema/protocol/mcpMessage/addition.csv declares (the null upstream drops from JSONValue, the protocol '
            'version pinned on the _meta field that names it). Definitions schema.ts leaves without a JSDoc take their text from '
            'rsc/schema/protocol/mcpMessage/description.csv; the definitions no message carries are declared in '
            'rsc/schema/protocol/mcpMessage/unreachable.csv. Every description ends with the definition\'s layer - the '
            "house's reading of the @category tag schema.ts carries, by rsc/schema/protocol/mcpMessage/layer.csv (the layers, "
            'each with its reading), category_layer.csv (category to layer) and placement.csv (what the tag and the '
            'composition cannot place) - so the schema reads '
            'by concern. One instance is one JSON-RPC message.'
        ),
        'allOf': [{'$ref': f'#/definitions/{ROOT_DEFINITION}'}],
        'definitions': ordered,
    }


def rendered(doc: dict) -> str:
    return json.dumps(doc, indent=2) + '\n'   # ascii-escaped, as every sibling family


# ── the witness ───────────────────────────────────────────────────────────────

def disagreements(house_doc: dict, snapshot_doc: dict, rows: list[dict], constants: dict) -> list[str]:
    """Every snapshot definition whose house counterpart, resolved and normalized, is
    not equal to it (resolved and normalized in its own document) - or is missing.
    Each addition row's house reading is set back to upstream's on the house side
    first, and a row upstream no longer bears is a disagreement of its own. Empty
    means agreement."""
    container = '$defs' if '$defs' in snapshot_doc else 'definitions'
    house = json.loads(json.dumps(house_doc.get('definitions', {})))
    snap = {name: to_house(body) for name, body in snapshot_doc[container].items()}
    out = []
    for row in rows:
        name, pointer = row['definition'], row['pointer']
        upstream, house_reading = _reading(row['upstream'], constants), _reading(row['house'], constants)
        try:
            found = _at(snap[name], pointer) if name in snap else None
        except (KeyError, IndexError, ValueError):
            found = None
        if not (found == upstream or (found is ABSENT and upstream is ABSENT)):
            out.append(f'{name}: {ADDITION.relative_to(REPO)} says upstream reads '
                       f'{"nothing" if upstream is ABSENT else json.dumps(upstream)} at {pointer!r}, and it does not - the row is stale')
            continue
        try:
            if name in house and _at(house[name], pointer) == house_reading:
                _set(house[name], pointer, upstream)
        except (KeyError, IndexError, ValueError):
            out.append(f'{name}: {ADDITION.relative_to(REPO)} names {pointer!r}, which the factoring does not have')
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
    """The flat house-dialect shapes schema.ts generates (plus the headers) and the
    composition it declares - what status reports overrides from."""
    shapes = generated().shapes()
    shapes.update({n: dict(b) for n, b in HEADERS.items()})
    return shapes, composition()


def inputs() -> tuple[dict, dict]:
    """(shapes, composition) - the derivation's inputs as generated now."""
    return shapes_and_declared()


def current_text() -> str:
    """The factoring as it should read now, from the committed inputs."""
    shapes, declared = inputs()
    return rendered(factored(shapes, descriptions(), declared, provenance(), unreachable(),
                             categories(), layer_rule(), placements(provenance()['lineage']),
                             additions(), generated().constants))
