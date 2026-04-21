#!/usr/bin/env python
"""Repair composition.base_schemas_closed — add additionalProperties:false to all ...Base schemas."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

count = 0
for name, defn in schema.get('definitions', {}).items():
    if name.endswith('Base') and defn.get('additionalProperties') is not False:
        defn['additionalProperties'] = False
        print(f'Fixed: {name}')
        count += 1

with open(sys.argv[1], 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Repaired composition.base_schemas_closed: {count} fixed')
