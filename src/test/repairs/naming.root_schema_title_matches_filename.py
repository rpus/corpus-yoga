#!/usr/bin/env python
"""Repair naming.root_schema_title_matches_filename — Set root title to filename stem.

Usage: python src/test/repairs/naming.root_schema_title_matches_filename.py <schema>

Writes back to the same file in place.
"""
import json
import sys
from pathlib import Path

schema_path = Path(sys.argv[1])
stem = schema_path.stem

with open(schema_path) as f:
    schema = json.load(f)

old = schema.get('title')
if old == stem:
    print(f'Nothing to fix: title already {stem!r}')
    sys.exit(0)

schema['title'] = stem
# Ensure title is still the first key
schema = {'title': stem, **{k: v for k, v in schema.items() if k != 'title'}}

tmp = schema_path.with_suffix('.tmp')
with open(tmp, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
tmp.replace(schema_path)
print(f'Fixed root title: {old!r} → {stem!r} in {schema_path}')
