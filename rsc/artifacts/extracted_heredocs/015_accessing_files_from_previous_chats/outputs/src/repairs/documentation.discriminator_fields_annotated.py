#!/usr/bin/env python3
"""Repair: annotate discriminator fields for all oneOf-referenced subtypes.
Usage: python documentation.discriminator_fields_annotated.py schema.json"""
import json, sys

path = sys.argv[1]
with open(path) as f:
    schema = json.load(f)
defs = schema['definitions']

oneof_refs = set()
def collect(obj):
    if isinstance(obj, dict):
        if 'oneOf' in obj:
            for b in obj['oneOf']:
                if '$ref' in b: oneof_refs.add(b['$ref'][len('#/definitions/'):])
        for v in obj.values(): collect(v)
    elif isinstance(obj, list):
        for v in obj: collect(v)
collect(schema)

for name in oneof_refs:
    defn = defs.get(name, {})
    for prop_name in ('type', 'name'):
        prop = defn.get('properties', {}).get(prop_name, {})
        if 'enum' in prop and len(prop['enum']) == 1:
            if 'discriminator' not in prop.get('description', '').lower():
                prop['description'] = '(discriminator)'
                print(f'Fixed: {name}/{prop_name}')

with open(path, 'w') as f:
    json.dump(schema, f, indent=2)