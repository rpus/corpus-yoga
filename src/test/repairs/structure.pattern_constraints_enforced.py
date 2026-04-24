#!/usr/bin/env python
"""Repair structure.pattern_constraints_enforced — Move regex from description to pattern field.

Usage: python src/test/repairs/structure.pattern_constraints_enforced.py <schema>

Scans descriptions for patterns like 'matches /regex/' or 'pattern: /regex/'
and, when found, extracts the regex into a sibling 'pattern' field.
Only acts when no 'pattern' field already exists.
Writes back to the same file in place.
"""
import json, re, sys

# Matches: matches /^foo$/, pattern: /^foo$/, regex /^foo$/
PATTERN_RE = re.compile(r'(?:matches|pattern[:\s]|regex)\s+/([^/]+)/', re.IGNORECASE)

schema_path = sys.argv[1]
with open(schema_path) as f:
    schema = json.load(f)

count = 0
def fix(obj, path=''):
    global count
    if isinstance(obj, dict):
        if 'description' in obj and 'pattern' not in obj:
            m = PATTERN_RE.search(obj['description'])
            if m:
                obj['pattern'] = m.group(1)
                count += 1
                print(f'  {path}: extracted pattern {m.group(1)!r}')
        for k, v in obj.items():
            fix(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            fix(v, f'{path}[{i}]')
fix(schema)

if count == 0:
    print('Nothing to fix (or patterns already enforced).')
    sys.exit(0)

with open(schema_path, 'w') as f:
    json.dump(schema, f, indent=2)
    f.write('\n')
print(f'Extracted {count} pattern(s) in {schema_path}')
