#!/usr/bin/env python3
"""naming.title_matches_key — Every definition's title matches its key.

Repair: src/repairs/naming.title_matches_key.py (batch fix all mismatches)
        src/repairs/naming.upper_camel_case.py   (if mismatch is due to a rename —
                                                  updates both key and title atomically)
"""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = [f'{n}: title={d.get("title")!r}'
         for n, d in schema.get('definitions', {}).items()
         if d.get('title') != n]

if fails:
    print(f'FAIL naming.title_matches_key:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS naming.title_matches_key')
