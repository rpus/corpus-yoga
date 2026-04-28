#!/usr/bin/env python
"""structure.no_redundant_additional_properties_true — No explicit additionalProperties: true."""
import json
import sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if obj.get('additionalProperties') is True:
            fails.append(path)
        for k, v in obj.items():
            check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check(v, f'{path}[{i}]')
check(schema)

if fails:
    print('FAIL structure.no_redundant_additional_properties_true:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS structure.no_redundant_additional_properties_true')
