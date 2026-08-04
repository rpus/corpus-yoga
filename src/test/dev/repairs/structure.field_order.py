#!/usr/bin/env python
"""Repair structure.field_order — Reorder keys so title, description come first.

Usage: python src/test/dev/repairs/structure.field_order.py <schema>

For every definition with title/description not in first two positions, rebuilds
the key order: title, description, then remaining keys in original order.
Writes back to the same file in place.
"""
import json
import sys
from pathlib import Path

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

fixed = 0
for name, defn in schema.get('definitions', {}).items():
    keys = list(defn.keys())
    if keys[:2] == ['title', 'description']:
        continue
    reordered = {}
    for k in ['title', 'description']:
        if k in defn:
            reordered[k] = defn[k]
    for k in keys:
        if k not in reordered:
            reordered[k] = defn[k]
    schema['definitions'][name] = reordered
    fixed += 1
    print(f'  Reordered: {name} ({keys[:3]} → title, description, ...)')

if fixed == 0:
    print('Nothing to fix.')
    sys.exit(0)

tmp = Path(schema_path).with_suffix('.tmp')
with open(tmp, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
tmp.replace(schema_path)
print(f'Fixed {fixed} definition(s) in {schema_path}')
