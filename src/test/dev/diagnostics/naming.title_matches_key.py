#!/usr/bin/env python
"""naming.title_matches_key — Every definition's title matches its key."""
import json
import sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = [f'{n}: title={d.get("title")!r}'
         for n, d in schema.get('definitions', {}).items()
         if d.get('title') != n]

if fails:
    print('FAIL naming.title_matches_key:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS naming.title_matches_key')
