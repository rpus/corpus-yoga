#!/usr/bin/env python
"""Repair naming.upper_camel_case — Rename non-UpperCamelCase definition keys.

Usage: python src/repairs/naming.upper_camel_case.py <schema> <old_name> <new_name>

Renames the definition key and updates all $ref strings throughout the schema.
Writes back to the same file in place.
"""
import json, re, sys

schema_path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]

if not re.match(r'^[A-Z][A-Za-z0-9]*$', new):
    print(f'ERROR: "{new}" is not UpperCamelCase')
    sys.exit(1)

with open(schema_path) as f:
    raw = f.read()

old_ref = f'"#/definitions/{old}"'
new_ref = f'"#/definitions/{new}"'
if old_ref not in raw:
    print(f'ERROR: no $ref to "{old}" found in {schema_path}')
    sys.exit(1)

raw = raw.replace(old_ref, new_ref)

schema = json.loads(raw)
defs = schema.get('definitions', {})
if old not in defs:
    print(f'ERROR: definition "{old}" not found')
    sys.exit(1)
defn = defs.pop(old)
if defn.get('title') == old:
    defn['title'] = new
defs[new] = defn
# Rebuild definitions in same key order with rename applied
ordered = {(new if k == old else k): v for k, v in
           [(new if k == old else k, defs[new if k == old else k])
            for k in list({**{old: None}, **defs}.keys()) if k in defs or k == old]}
schema['definitions'] = {new if k == old else k: defs.get(new if k == old else k, defs.get(k))
                          for k in list(defs.keys())}

with open(schema_path, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')

print(f'Renamed "{old}" → "{new}" and updated all $refs in {schema_path}')
