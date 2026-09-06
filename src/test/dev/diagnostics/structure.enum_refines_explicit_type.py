#!/usr/bin/env python
"""structure.enum_refines_explicit_type — Every enum declares the single explicit type it refines.

An enum is a refinement of one base type, so it must say which: a subschema with "enum" must
also have a string "type", and the enum's values must all be of that type. (Values being
single-typed is necessary but not sufficient — the type must be stated, not left implicit.)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # src/ - modules both tiers import
from schema_walk import schema_nodes  # noqa: E402


def json_type(v):
    if isinstance(v, bool):
        return 'boolean'
    if isinstance(v, str):
        return 'string'
    if isinstance(v, int):
        return 'integer'
    if isinstance(v, float):
        return 'number'
    if v is None:
        return 'null'
    return type(v).__name__


with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
for path, s in schema_nodes(schema):
    if not (isinstance(s, dict) and 'enum' in s):
        continue
    value_types = sorted({json_type(v) for v in s['enum']})
    if 'type' not in s:
        fails.append(f'{path}: enum has no explicit "type" (values are {value_types})')
    elif not isinstance(s['type'], str):
        fails.append(f'{path}: "type" must be a single type, got {s["type"]!r}')
    elif value_types != [s['type']]:
        fails.append(f'{path}: "type": {s["type"]!r} does not match enum value types {value_types}')

if fails:
    print('FAIL structure.enum_refines_explicit_type:')
    for x in fails:
        print(f'  {x}')
    sys.exit(1)
print('PASS structure.enum_refines_explicit_type')
