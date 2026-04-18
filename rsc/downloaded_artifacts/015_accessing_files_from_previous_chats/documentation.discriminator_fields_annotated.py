#!/usr/bin/env python3
"""documentation.discriminator_fields_annotated — Discriminator fields annotated with (discriminator)."""
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

fails = []
for name in oneof_refs:
    defn = defs.get(name, {})
    for prop_name in ('type', 'name'):
        prop = defn.get('properties', {}).get(prop_name, {})
        if 'enum' in prop and len(prop['enum']) == 1:
            if 'discriminator' not in prop.get('description', '').lower():
                fails.append(f'{name}/properties/{prop_name}: {prop["enum"]}')

if fails:
    print('FAIL documentation.discriminator_fields_annotated:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS documentation.discriminator_fields_annotated')
