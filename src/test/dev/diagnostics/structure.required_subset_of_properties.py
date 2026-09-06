#!/usr/bin/env python
"""structure.required_subset_of_properties — Every required field is listed in properties."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # src/ - modules both tiers import
from schema_walk import schema_nodes  # noqa: E402

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
for path, node in schema_nodes(schema):
    if 'required' in node and 'properties' in node:
        props = set(node['properties'].keys())
        for name in node['required']:
            if name not in props:
                fails.append(f'{path}: required "{name}" not in properties')

if fails:
    print('FAIL structure.required_subset_of_properties:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS structure.required_subset_of_properties')
