#!/usr/bin/env python3
"""composition.no_additional_properties_on_subtypes — Subtypes must not combine additionalProperties:false with allOf referencing a schema with properties."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

fails = []
for name, defn in defs.items():
    if defn.get('additionalProperties') is False and 'allOf' in defn:
        for ref_obj in defn.get('allOf', []):
            ref = ref_obj.get('$ref', '')[len('#/definitions/'):]
            if ref and defs.get(ref, {}).get('properties'):
                fails.append(f'{name}: additionalProperties:false + allOf -> {ref}')

if fails:
    print('FAIL composition.no_additional_properties_on_subtypes:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS composition.no_additional_properties_on_subtypes')
