#!/usr/bin/env python3
"""Repair: reorder title/description to front of all definitions.
Usage: python structure.field_order.py schema.json"""
import json, sys

path = sys.argv[1]
with open(path) as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    ordered = {}
    for k in ['title', 'description']:
        if k in defn:
            ordered[k] = defn[k]
    for k, v in defn.items():
        if k not in ordered:
            ordered[k] = v
    schema['definitions'][name] = ordered
with open(path, 'w') as f:
    json.dump(schema, f, indent=2)
print('Field order fixed')