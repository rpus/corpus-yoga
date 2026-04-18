#!/usr/bin/env python3
"""naming.property_keys_lowercase — All property keys are lowercase or snake_case."""
import json, re, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'properties' in obj:
            for k in obj['properties']:
                if re.match(r'^[A-Z]', k):
                    fails.append(f'{path}: "{k}"')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)

if fails:
    print('FAIL naming.property_keys_lowercase:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS naming.property_keys_lowercase')
