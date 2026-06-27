#!/usr/bin/env python
"""Repair structure.enum_refines_explicit_type — Insert the explicit "type" each enum refines.

For every enum subschema lacking "type", infer the (single) type from its values and insert a
"type": "<T>" line immediately before "enum", at matching indentation. Done as a TEXTUAL edit
(not a json.dump round-trip) so the rest of the file's formatting -- e.g. hand-compacted
{"type": "null"} objects -- is left untouched. One inserted line per fixed enum.

Usage: python src/test/repairs/structure.enum_refines_explicit_type.py <schema>
"""
import json
import re
import sys
from pathlib import Path


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


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


path = sys.argv[1]
text = Path(path).read_text()
schema = json.loads(text)

# Each enum subschema in document order -> the type to insert, or None if it already has one.
needs = []
for s in walk(schema):
    if isinstance(s, dict) and 'enum' in s:
        needs.append(None if 'type' in s or not s['enum'] else json_type(s['enum'][0]))

# "enum" key lines, in document order (a JSON dfs in dict order matches file order).
lines = text.split('\n')
enum_lines = [i for i, l in enumerate(lines) if re.match(r'\s*"enum":', l)]

if len(enum_lines) != len(needs):
    sys.exit(f'mismatch: {len(enum_lines)} "enum" lines vs {len(needs)} enum subschemas in {path}')

fix_at = {enum_lines[i]: t for i, t in enumerate(needs) if t is not None}
if not fix_at:
    print('Nothing to fix.')
    sys.exit(0)

out = []
for i, l in enumerate(lines):
    if i in fix_at:
        indent = l[:len(l) - len(l.lstrip())]
        out.append(f'{indent}"type": "{fix_at[i]}",')
    out.append(l)

Path(path).write_text('\n'.join(out))
print(f'Inserted "type" on {len(fix_at)} enum(s) in {path}')
