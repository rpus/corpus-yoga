#!/usr/bin/env python
"""Repair naming.title_matches_key — Set every definition's title to match its key.

Usage: python src/test/repairs/naming.title_matches_key.py <schema>

Overwrites title with the definition key for every definition where they differ.
Writes back to the same file in place.
"""
import json, sys
from pathlib import Path

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

fixed = 0
for name, defn in schema.get('definitions', {}).items():
    if defn.get('title') != name:
        print(f'  Fix: {name} title {defn.get("title")!r} → {name!r}')
        defn['title'] = name
        fixed += 1

if fixed == 0:
    print('Nothing to fix.')
    sys.exit(0)

tmp = Path(schema_path).with_suffix('.tmp')
with open(tmp, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
tmp.replace(schema_path)
print(f'Fixed {fixed} definition(s) in {schema_path}')
