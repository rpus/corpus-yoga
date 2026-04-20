#!/usr/bin/env python3
"""Repair: move definitions to bottom of root schema.
Usage: python structure.definitions_at_bottom.py schema.json"""
import json, sys

path = sys.argv[1]
with open(path) as f:
    schema = json.load(f)
defs = schema.pop('definitions')
schema['definitions'] = defs
with open(path, 'w') as f:
    json.dump(schema, f, indent=2)
print('Moved definitions to bottom')