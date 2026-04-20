#!/usr/bin/env python3
"""Repair: set title to match key for all mismatches.
Usage: python naming.title_matches_key.py schema.json"""
import json, sys

path = sys.argv[1]
with open(path) as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    if defn.get('title') != name:
        defn['title'] = name
        print(f'Fixed: {name}')
with open(path, 'w') as f:
    json.dump(schema, f, indent=2)