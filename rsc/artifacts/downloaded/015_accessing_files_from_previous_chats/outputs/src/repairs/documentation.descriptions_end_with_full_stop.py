#!/usr/bin/env python3
"""Repair: append missing full stop to descriptions lacking terminal punctuation.
Usage: python documentation.descriptions_end_with_full_stop.py schema.json"""
import json, re, sys

URL_RE = re.compile(r'https?://\S+$')
def valid_end(d):
    return (d.endswith('.') or d.endswith(')')
            or d.endswith('$') or bool(URL_RE.search(d))
            or d.endswith('.json'))

path = sys.argv[1]
with open(path) as f:
    schema = json.load(f)

def fix(obj):
    if isinstance(obj, dict):
        if 'description' in obj and isinstance(obj['description'], str):
            d = obj['description']
            if d and not valid_end(d):
                obj['description'] = d + '.'
                print(f'Fixed: ...{d[-30:]!r}')
        for v in obj.values(): fix(v)
    elif isinstance(obj, list):
        for v in obj: fix(v)
fix(schema)

with open(path, 'w') as f:
    json.dump(schema, f, indent=2)