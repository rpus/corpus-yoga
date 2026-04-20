#!/usr/bin/env python3
"""Repair: rename a definition to UpperCamelCase and update all $refs.
Usage: python naming.upper_camel_case.py schema.json OldName NewName"""
import json, sys

path, OLD, NEW = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path).read()
text = text.replace(f'"#/definitions/{OLD}"', f'"#/definitions/{NEW}"')
schema = json.loads(text)
schema['definitions'][NEW] = schema['definitions'].pop(OLD)
schema['definitions'][NEW]['title'] = NEW
with open(path, 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Renamed {OLD!r} -> {NEW!r}')