#!/usr/bin/env python3
"""composition.base_not_used_directly — Base schemas are never referenced directly from oneOf lists."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})
base_names = {n for n in defs if n.endswith('Base')}

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'oneOf' in obj:
            for b in obj['oneOf']:
                ref = b.get('$ref', '')[len('#/definitions/'):]
                if ref in base_names:
                    fails.append(f'{path}: {ref!r} in oneOf')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)

if fails:
    print('FAIL composition.base_not_used_directly:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS composition.base_not_used_directly')