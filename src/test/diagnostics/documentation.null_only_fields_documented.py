#!/usr/bin/env python
"""documentation.null_only_fields_documented — null-typed fields note their empirical basis."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

fails = []

for name, defn in defs.items():
    if defn.get('type') == 'null':
        d = defn.get('description', '')
        if 'null' not in d.lower() and 'observed' not in d.lower():
            fails.append(f'definition {name}')

def check_props(obj, path=''):
    if isinstance(obj, dict):
        if 'properties' in obj:
            for k, v in obj['properties'].items():
                if isinstance(v, dict) and v.get('type') == 'null':
                    d = v.get('description', '')
                    if 'null' not in d.lower() and 'observed' not in d.lower():
                        fails.append(f'{path}/properties/{k}')
        for k, v in obj.items():
            if k != 'oneOf': check_props(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check_props(v, f'{path}[{i}]')
check_props({'definitions': defs})

if fails:
    print('FAIL documentation.null_only_fields_documented:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS documentation.null_only_fields_documented')
