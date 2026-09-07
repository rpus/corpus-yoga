#!/usr/bin/env python
"""
schema_walk.py - the one JSON Schema walk both tiers share (the diagnostics, the
protocol factoring), DERIVED from the committed draft-04 meta-schema
(rsc/reference/JSONSchema/draft-04/schema.json) rather than restated (#571).

Every keyword's position is what the meta-schema's own `properties` entry says it
is: `{"$ref": "#"}` is a schema (`not`); an object whose `additionalProperties` is a
schema is a map of schemas (`properties`, `patternProperties`, `definitions`); an
array whose `items` is a schema is a list of schemas (`allOf`, `anyOf`, `oneOf`,
via `schemaArray`); an `anyOf` is either of its branches (`items`: a schema or a
list of them; `additionalProperties`, `additionalItems`: a boolean or a schema;
`dependencies`: a map whose members are each a schema or a string array); anything
else is a plain value. So a property named `enum`, `oneOf`, `required` or
`properties` is a name, never a keyword, and a keyword the meta-schema does not
declare is UNKNOWN - never descended, and reported by
structure.keywords_declared. The one keyword outside the meta-schema is `$ref`, a
value position: JSON Reference (draft-pbryan-zyp-json-ref-03), which draft-04
defers to rather than declares.
"""

import json
from pathlib import Path

SELF = 'src/schema_walk.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

META_SCHEMA = REPO / 'rsc/reference/JSONSchema/draft-04/schema.json'
JSON_REFERENCE_KEYWORDS = {'$ref': ('value',)}     # JSON Reference, not the meta-schema's

# position descriptors: ('schema',) | ('list', inner) | ('map', inner) | ('either', [inner, ...]) | ('value',)
SCHEMA, VALUE = ('schema',), ('value',)


def _meta() -> dict:
    return json.loads(META_SCHEMA.read_text())


def _position(spec: dict, meta: dict, _seen=()) -> tuple:
    """The position a meta-schema subschema assigns to the value it describes."""
    if spec == {'$ref': '#'}:
        return SCHEMA
    ref = spec.get('$ref')
    if isinstance(ref, str) and ref.startswith('#/definitions/'):
        name = ref.split('/')[-1]
        if name in _seen:
            return VALUE
        return _position(meta['definitions'][name], meta, _seen + (name,))
    if isinstance(spec.get('anyOf'), list):
        branches = [_position(b, meta, _seen) for b in spec['anyOf']]
        branches = [b for b in branches if b != VALUE] or [VALUE]
        return ('either', branches) if len(branches) > 1 else branches[0]
    if spec.get('type') == 'object' and isinstance(spec.get('additionalProperties'), dict):
        inner = _position(spec['additionalProperties'], meta, _seen)
        return ('map', inner) if inner != VALUE else VALUE
    if spec.get('type') == 'array' and isinstance(spec.get('items'), dict):
        inner = _position(spec['items'], meta, _seen)
        return ('list', inner) if inner != VALUE else VALUE
    return VALUE


def _positions() -> dict[str, tuple]:
    meta = _meta()
    out = {key: _position(spec, meta) for key, spec in meta['properties'].items()}
    out.update(JSON_REFERENCE_KEYWORDS)
    return out


POSITIONS: dict[str, tuple] = _positions()
KEYWORDS = frozenset(POSITIONS)


def kind(key: str):
    """The position descriptor of a keyword, or None for a key the dialect does not
    declare (draft-04's meta-schema plus JSON Reference)."""
    return POSITIONS.get(key)


def _children(position: tuple, value, path: str):
    """(pointer, subschema) for every schema the value holds at this position."""
    tag = position[0]
    if tag == 'schema':
        if isinstance(value, dict):
            yield path, value
    elif tag == 'list':
        if isinstance(value, list):
            for i, sub in enumerate(value):
                yield from _children(position[1], sub, f'{path}/{i}')
    elif tag == 'map':
        if isinstance(value, dict):
            for name, sub in value.items():
                yield from _children(position[1], sub, f'{path}/{name}')
    elif tag == 'either':
        for branch in position[1]:
            fits = (branch[0] == 'list' and isinstance(value, list)) or \
                   (branch[0] in ('schema', 'map') and isinstance(value, dict)) or \
                   branch[0] == 'either'
            if fits:
                yield from _children(branch, value, path)
                return


def schema_nodes(schema, path: str = '#'):
    """(pointer, node) for every dict in schema position under schema, the node
    before its descendants, in document order."""
    if not isinstance(schema, dict):
        return
    yield path, schema
    for key, value in schema.items():
        position = POSITIONS.get(key)
        if position:
            for sub_path, sub in _children(position, value, f'{path}/{key}'):
                yield from schema_nodes(sub, sub_path)


def _rebuilt_at(position: tuple, value, child):
    tag = position[0]
    if tag == 'schema':
        return child(value) if isinstance(value, dict) else value
    if tag == 'list':
        return [_rebuilt_at(position[1], sub, child) for sub in value] if isinstance(value, list) else value
    if tag == 'map':
        return {name: _rebuilt_at(position[1], sub, child) for name, sub in value.items()} if isinstance(value, dict) else value
    if tag == 'either':
        for branch in position[1]:
            fits = (branch[0] == 'list' and isinstance(value, list)) or \
                   (branch[0] in ('schema', 'map') and isinstance(value, dict)) or \
                   branch[0] == 'either'
            if fits:
                return _rebuilt_at(branch, value, child)
    return value


def rebuilt(node: dict, child) -> dict:
    """node with `child` applied to every schema it holds directly (one level: the
    caller recurses), keyword values that are not schemas left as they are - the
    grammar-aware map a transform is written with."""
    out = {}
    for key, value in node.items():
        position = POSITIONS.get(key)
        out[key] = _rebuilt_at(position, value, child) if position else value
    return out
