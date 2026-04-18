#!/usr/bin/env python3
"""Repair documentation.descriptions_end_with_full_stop — Append period to unterminated descriptions.

Usage: python src/repairs/documentation.descriptions_end_with_full_stop.py <schema>

Appends '.' to any description string that doesn't end with recognised terminal
punctuation (. ) $ or URL). Writes back to the same file in place.

Diagnostic pre/post conditions:
  documentation.descriptions_end_with_full_stop    FAIL → PASS
"""
import json, re, sys

URL_RE = re.compile(r'https?://\S+$')

def valid_end(d):
    return (d.endswith('.') or d.endswith(')')
            or d.endswith('$') or bool(URL_RE.search(d))
            or d.endswith('.json'))

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

count = 0
def fix(obj, path=''):
    global count
    if isinstance(obj, dict):
        if 'description' in obj and isinstance(obj['description'], str):
            d = obj['description']
            if d and not valid_end(d):
                obj['description'] = d + '.'
                count += 1
                print(f'  {path}: appended . to ...{d[-30:]!r}')
        for k, v in obj.items():
            fix(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            fix(v, f'{path}[{i}]')
fix(schema)

if count == 0:
    print('Nothing to fix.')
    sys.exit(0)

with open(schema_path, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
print(f'Fixed {count} description(s) in {schema_path}')
