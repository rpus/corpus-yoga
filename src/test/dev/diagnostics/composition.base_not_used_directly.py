#!/usr/bin/env python
"""composition.base_not_used_directly — Base schemas are never referenced directly from oneOf lists."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/test/dev - the diagnostics' shared walk
from schema_walk import schema_nodes  # noqa: E402

with open(sys.argv[1]) as f:
    schema = json.load(f)

defs = schema.get('definitions', {})
base_names = {n for n in defs if n.endswith('Base')}
fails = []
for path, node in schema_nodes(schema):
    for b in node.get('oneOf', []):
        ref = b.get('$ref', '')[len('#/definitions/'):]
        if ref in base_names:
            fails.append(f'{path}: {ref!r} in oneOf')

if fails:
    print('FAIL composition.base_not_used_directly:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS composition.base_not_used_directly')
