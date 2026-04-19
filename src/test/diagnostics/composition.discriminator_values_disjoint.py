#!/usr/bin/env python
"""composition.discriminator_values_disjoint — Discriminator enum values across oneOf branches are disjoint."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

def get_disc_vals(ref):
    name = ref[len('#/definitions/'):]
    for prop in defs.get(name, {}).get('properties', {}).values():
        if 'enum' in prop: return set(prop['enum'])
    return set()

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'oneOf' in obj:
            seen = set()
            for branch in obj['oneOf']:
                vals = get_disc_vals(branch.get('$ref', ''))
                overlap = seen & vals
                if overlap: fails.append(f'{path}: {overlap}')
                seen |= vals
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)

if fails:
    print('FAIL composition.discriminator_values_disjoint:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS composition.discriminator_values_disjoint')
