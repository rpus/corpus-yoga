#!/usr/bin/env python
"""Repair composition.base_schemas_closed — add additionalProperties:false to all ...Base schemas."""
import json, sys
from pathlib import Path

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

count = 0
for name, defn in schema.get('definitions', {}).items():
    if name.endswith('Base') and defn.get('additionalProperties') is not False:
        defn['additionalProperties'] = False
        print(f'Fixed: {name}')
        count += 1

tmp = Path(schema_path).with_suffix('.tmp')
with open(tmp, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
tmp.replace(schema_path)
print(f'Repaired composition.base_schemas_closed: {count} fixed')
