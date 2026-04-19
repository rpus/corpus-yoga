#!/usr/bin/env python3
"""structure.required_subset_of_properties — Every required field is listed in properties."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'required' in obj and 'properties' in obj:
            props = set(obj['properties'].keys())
            for f in obj['required']:
                if f not in props:
                    fails.append(f'{path}: required "{f}" not in properties')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)

if fails:
    print('FAIL structure.required_subset_of_properties:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS structure.required_subset_of_properties')
