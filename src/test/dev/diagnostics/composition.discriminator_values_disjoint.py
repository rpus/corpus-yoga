#!/usr/bin/env python
"""composition.discriminator_values_disjoint — Discriminator enum values across oneOf branches are disjoint."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # src/ - modules both tiers import
from schema_walk import schema_nodes  # noqa: E402

with open(sys.argv[1]) as f:
    schema = json.load(f)

defs = schema.get('definitions', {})

def get_disc_vals(ref):
    name = ref[len('#/definitions/'):]
    for prop in defs.get(name, {}).get('properties', {}).values():
        if isinstance(prop, dict) and 'enum' in prop:
            return set(prop['enum'])
    return set()

fails = []
for path, node in schema_nodes(schema):
    if 'oneOf' not in node:
        continue
    seen = set()
    for branch in node['oneOf']:
        vals = get_disc_vals(branch.get('$ref', ''))
        overlap = seen & vals
        if overlap:
            fails.append(f'{path}: {overlap}')
        seen |= vals

if fails:
    print('FAIL composition.discriminator_values_disjoint:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS composition.discriminator_values_disjoint')
