#!/usr/bin/env python
"""
schema_walk.py - the one JSON Schema walk the diagnostics share: every dict in
SCHEMA position, never a properties map read as a schema. At a schema node the
values of `properties`, `patternProperties`, `definitions` and `$defs` are schemas
(the map itself is not); `items` (a schema, or a list of them), `additionalItems`,
`additionalProperties` and `not` are schemas; the members of `allOf`, `anyOf` and
`oneOf` are schemas; every other key is a keyword's value. So a property named
`enum`, `oneOf`, `required` or `properties` - the MCP schema's schema-describing
definitions have them all - is never read as the keyword.
"""

from pathlib import Path

SELF = 'src/test/dev/schema_walk.py'
_file = Path(__file__).resolve()
assert [p for p in _file.parents if p / SELF == _file], f'{_file} is not at its declared address {SELF}'

SCHEMA_MAPS = ('properties', 'patternProperties', 'definitions', '$defs')
SCHEMA_LISTS = ('allOf', 'anyOf', 'oneOf')
SCHEMA_SINGLETONS = ('additionalProperties', 'additionalItems', 'not')


def schema_nodes(schema, path: str = '#'):
    """(pointer, node) for every dict in schema position under schema, the node
    before its descendants, in document order."""
    if not isinstance(schema, dict):
        return
    yield path, schema
    for key, value in schema.items():
        if key in SCHEMA_MAPS and isinstance(value, dict):
            for name, sub in value.items():
                yield from schema_nodes(sub, f'{path}/{key}/{name}')
        elif key in SCHEMA_LISTS and isinstance(value, list):
            for i, sub in enumerate(value):
                yield from schema_nodes(sub, f'{path}/{key}/{i}')
        elif key == 'items':
            if isinstance(value, list):
                for i, sub in enumerate(value):
                    yield from schema_nodes(sub, f'{path}/items/{i}')
            else:
                yield from schema_nodes(value, f'{path}/items')
        elif key in SCHEMA_SINGLETONS and isinstance(value, dict):
            yield from schema_nodes(value, f'{path}/{key}')
