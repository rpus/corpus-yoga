#!/usr/bin/env python3
"""composition.wrapper_has_five_fields — Union wrapper schemas have exactly title, description, type, allOf, oneOf."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

expected = {'title', 'description', 'type', 'allOf', 'oneOf'}
fails = [f'{n}: {sorted(set(d.keys()))}'
         for n, d in schema.get('definitions', {}).items()
         if 'oneOf' in d and 'allOf' in d and set(d.keys()) != expected]

if fails:
    print('FAIL composition.wrapper_has_five_fields:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS composition.wrapper_has_five_fields')