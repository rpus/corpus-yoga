#!/usr/bin/env python
"""Repair documentation.discriminator_fields_annotated — annotate discriminator fields with (discriminator)."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

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

count = 0
for name in oneof_refs:
    defn = defs.get(name, {})
    for prop_name in ('type', 'name'):
        prop = defn.get('properties', {}).get(prop_name, {})
        if 'enum' in prop and len(prop['enum']) == 1:
            if 'discriminator' not in prop.get('description', '').lower():
                prop['description'] = '(discriminator)'
                print(f'Fixed: {name}/{prop_name}')
                count += 1

with open(sys.argv[1], 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Repaired documentation.discriminator_fields_annotated: {count} fixed')
