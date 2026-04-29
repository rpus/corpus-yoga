#!/usr/bin/env python
"""structure.definitions_at_bottom — definitions is the last key in the root schema."""
import json
import sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

keys = list(schema.keys())
if 'definitions' not in keys:
    print('PASS structure.definitions_at_bottom (no definitions)')
    sys.exit(0)
if keys[-1] != 'definitions':
    print(f'FAIL structure.definitions_at_bottom: at position {keys.index("definitions")+1} of {len(keys)}')
    sys.exit(1)
print('PASS structure.definitions_at_bottom')
