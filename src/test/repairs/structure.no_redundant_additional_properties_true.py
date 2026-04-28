#!/usr/bin/env python
"""Repair structure.no_redundant_additional_properties_true — Remove explicit additionalProperties: true.

Usage: python src/test/repairs/structure.no_redundant_additional_properties_true.py <schema>

Writes back to the same file in place.
"""
import json
import sys
from pathlib import Path

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

count = 0
def strip(obj, path=''):
    global count
    if isinstance(obj, dict):
        if obj.get('additionalProperties') is True:
            del obj['additionalProperties']
            count += 1
            print(f'  Removed additionalProperties:true at {path}')
        for k, v in obj.items():
            strip(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            strip(v, f'{path}[{i}]')
strip(schema)

if count == 0:
    print('Nothing to fix.')
    sys.exit(0)

tmp = Path(schema_path).with_suffix('.tmp')
with open(tmp, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
tmp.replace(schema_path)
print(f'Removed {count} instance(s) in {schema_path}')
