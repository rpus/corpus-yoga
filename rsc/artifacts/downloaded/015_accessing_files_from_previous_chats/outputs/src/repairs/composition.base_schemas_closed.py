#!/usr/bin/env python3
"""Repair: add additionalProperties: false to all ...Base schemas missing it.
Usage: python composition.base_schemas_closed.py schema.json"""
import json, sys

path = sys.argv[1]
with open(path) as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    if name.endswith('Base') and defn.get('additionalProperties') is not False:
        defn['additionalProperties'] = False
        print(f'Fixed: {name}')
with open(path, 'w') as f:
    json.dump(schema, f, indent=2)