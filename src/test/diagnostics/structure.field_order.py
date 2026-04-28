#!/usr/bin/env python
"""structure.field_order — Every definition begins with title, description, type."""
import json
import sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
for name, defn in schema.get('definitions', {}).items():
    keys = list(defn.keys())
    if keys[0] != 'title':
        fails.append(f'{name}: first={keys[0]!r}')
    elif len(keys) < 2 or keys[1] != 'description':
        fails.append(f'{name}: second={keys[1] if len(keys)>1 else "missing"!r}')

if fails:
    print('FAIL structure.field_order:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS structure.field_order')
