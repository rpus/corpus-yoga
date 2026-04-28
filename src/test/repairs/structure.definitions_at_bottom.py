#!/usr/bin/env python
"""Repair structure.definitions_at_bottom — Move definitions to last key.

Usage: python src/test/repairs/structure.definitions_at_bottom.py <schema>

Writes back to the same file in place.
"""
import json, sys
from pathlib import Path

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

keys = list(schema.keys())
if keys[-1] == 'definitions':
    print('Nothing to fix: definitions already last.')
    sys.exit(0)

defs = schema.pop('definitions')
schema['definitions'] = defs

tmp = Path(schema_path).with_suffix('.tmp')
with open(tmp, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
tmp.replace(schema_path)
print(f'Moved definitions to last key in {schema_path}')
