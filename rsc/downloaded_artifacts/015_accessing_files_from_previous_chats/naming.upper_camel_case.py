#!/usr/bin/env python3
"""naming.upper_camel_case — All definition names are UpperCamelCase."""
import json, re, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = [n for n in schema.get('definitions', {})
         if not re.match(r'^[A-Z][A-Za-z0-9]*$', n)]

if fails:
    print(f'FAIL naming.upper_camel_case: {fails}')
    sys.exit(1)
print('PASS naming.upper_camel_case')
