#!/usr/bin/env python
"""Repair structure.required_subset_of_properties — Remove required entries absent from properties.

Usage: python src/test/repairs/structure.required_subset_of_properties.py <schema>

Writes back to the same file in place.
"""
import json, sys

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

count = 0
def fix(obj, path=''):
    global count
    if isinstance(obj, dict):
        if 'required' in obj and 'properties' in obj:
            props = set(obj['properties'].keys())
            before = obj['required']
            after = [f for f in before if f in props]
            removed = [f for f in before if f not in props]
            if removed:
                obj['required'] = after
                count += len(removed)
                print(f'  {path}: removed {removed} from required')
        for k, v in obj.items():
            fix(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            fix(v, f'{path}[{i}]')
fix(schema)

if count == 0:
    print('Nothing to fix.')
    sys.exit(0)

with open(schema_path, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
print(f'Removed {count} errant required field(s) in {schema_path}')
