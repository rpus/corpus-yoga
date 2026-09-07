#!/usr/bin/env python
"""empirical.oneOf_branches_evidenced — No oneOf branch is annotated as unevidenced."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # src/ - modules both tiers import
from schema_walk import schema_nodes  # noqa: E402

with open(sys.argv[1]) as f:
    schema = json.load(f)

defs = schema.get('definitions', {})
oneof_branches = set()
for _, node in schema_nodes(schema):
    for b in node.get('oneOf', []):
        ref = b.get('$ref', '')
        if ref.startswith('#/definitions/'):
            oneof_branches.add(ref[len('#/definitions/'):])

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
