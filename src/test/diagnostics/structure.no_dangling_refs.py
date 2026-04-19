#!/usr/bin/env python
"""structure.no_dangling_refs — Every $ref target exists in definitions."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = set(schema.get('definitions', {}).keys())

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if '$ref' in obj:
            t = obj['$ref']
            if t.startswith('#/definitions/'):
                name = t[len('#/definitions/'):]
                if name not in defs:
                    fails.append(f'{path}: dangling $ref to "{name}"')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)

if fails:
    print('FAIL structure.no_dangling_refs:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS structure.no_dangling_refs')
