#!/usr/bin/env python
"""Repair documentation.every_definition_has_title_and_description — Add stub title/description.

Usage: python src/test/repairs/documentation.every_definition_has_title_and_description.py <schema>

Inserts placeholder title (definition name) and description ("TODO: document.")
for any definition missing either. Writes back to the same file in place.
"""
import json, sys

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

fixed = 0
for name, defn in schema.get('definitions', {}).items():
    if 'title' not in defn:
        defn['title'] = name
        fixed += 1
        print(f'  Added title to {name}')
    if 'description' not in defn:
        defn['description'] = 'TODO: document.'
        fixed += 1
        print(f'  Added description stub to {name}')

if fixed == 0:
    print('Nothing to fix.')
    sys.exit(0)

with open(schema_path, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
print(f'Fixed {fixed} field(s) in {schema_path}')
