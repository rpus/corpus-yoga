#!/usr/bin/env python
"""empirical.oneOf_branches_evidenced — No oneOf branch is annotated as unevidenced."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

# Collect all definition names that appear as $ref branches in any oneOf.
oneof_branches = set()
def collect(obj):
    if isinstance(obj, dict):
        if 'oneOf' in obj:
            for b in obj['oneOf']:
                ref = b.get('$ref', '')
                if ref.startswith('#/definitions/'):
                    oneof_branches.add(ref[len('#/definitions/'):])
        for v in obj.values():
            collect(v)
    elif isinstance(obj, list):
        for v in obj:
            collect(v)
collect(schema)

fails = []
for name in oneof_branches:
    defn = defs.get(name, {})
    desc = (defn.get('description') or '').lower()
    if 'not observed' in desc:
        fails.append(f'{name}: annotated as unevidenced — remove or evidence before committing')

if fails:
    print('FAIL empirical.oneOf_branches_evidenced:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS empirical.oneOf_branches_evidenced')
