#!/usr/bin/env python3
"""Repair structure.no_redundant_additional_properties_true — Remove explicit additionalProperties: true.

Usage: python src/repairs/structure.no_redundant_additional_properties_true.py <schema>

Writes back to the same file in place.

Diagnostic pre/post conditions:
  structure.no_redundant_additional_properties_true    FAIL → PASS
  composition.no_additional_properties_on_subtypes     unaffected    (checks for false, not true)
"""
import json, sys

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

with open(schema_path, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
print(f'Removed {count} instance(s) in {schema_path}')
