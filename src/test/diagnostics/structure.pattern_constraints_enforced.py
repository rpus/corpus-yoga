#!/usr/bin/env python
"""structure.pattern_constraints_enforced — String fields with regex in description must have pattern."""
import json, re, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

REGEX_RE = re.compile(r'Regex:|^\^.+\$$', re.MULTILINE)

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if obj.get('type') == 'string':
            d = obj.get('description', '') or ''
            if REGEX_RE.search(d) and 'pattern' not in obj:
                fails.append(path)
        for k, v in obj.items():
            check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check(v, f'{path}[{i}]')
check(schema)

if fails:
    print('FAIL structure.pattern_constraints_enforced:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS structure.pattern_constraints_enforced')
