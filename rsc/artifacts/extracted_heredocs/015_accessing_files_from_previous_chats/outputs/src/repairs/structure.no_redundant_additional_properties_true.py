#!/usr/bin/env python3
"""Repair: remove all explicit additionalProperties: true.
Usage: python structure.no_redundant_additional_properties_true.py schema.json"""
import json, sys

path = sys.argv[1]
with open(path) as f:
    schema = json.load(f)
count = 0
def fix(obj):
    global count
    if isinstance(obj, dict):
        if obj.get('additionalProperties') is True:
            del obj['additionalProperties']
            count += 1
        for v in obj.values(): fix(v)
    elif isinstance(obj, list):
        for v in obj: fix(v)
fix(schema)
with open(path, 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Removed {count} occurrences')