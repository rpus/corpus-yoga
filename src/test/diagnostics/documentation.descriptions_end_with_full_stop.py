#!/usr/bin/env python
"""documentation.descriptions_end_with_full_stop — All descriptions end with recognised terminal punctuation."""
import json, re, sys

URL_RE = re.compile(r'https?://\S+$')

def valid_end(d):
    return (d.endswith('.') or d.endswith(')')
            or d.endswith('$') or bool(URL_RE.search(d))
            or d.endswith('.json'))

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'description' in obj and isinstance(obj['description'], str):
            d = obj['description']
            if d and not valid_end(d):
                fails.append(f'{path}: ...{d[-40:]!r}')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)

if fails:
    print('FAIL documentation.descriptions_end_with_full_stop:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS documentation.descriptions_end_with_full_stop')
