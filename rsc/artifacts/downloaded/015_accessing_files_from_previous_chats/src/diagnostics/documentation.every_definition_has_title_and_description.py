#!/usr/bin/env python3
"""documentation.every_definition_has_title_and_description — Every definition has title and description.

Repair: src/repairs/documentation.every_definition_has_title_and_description.py
        Note: also fixes naming.title_matches_key if a missing title was the only violation there.
"""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
for name, defn in schema.get('definitions', {}).items():
    if 'title' not in defn: fails.append(f'{name}: missing title')
    if 'description' not in defn: fails.append(f'{name}: missing description')

if fails:
    print('FAIL documentation.every_definition_has_title_and_description:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS documentation.every_definition_has_title_and_description')
