#!/usr/bin/env python3
"""composition.base_schemas_closed — All ...Base schemas have additionalProperties: false."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = [n for n, d in schema.get('definitions', {}).items()
         if n.endswith('Base') and d.get('additionalProperties') is not False]

if fails:
    print(f'FAIL composition.base_schemas_closed: {fails}')
    sys.exit(1)
print('PASS composition.base_schemas_closed')