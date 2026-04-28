#!/usr/bin/env python
"""empirical.nullable_fields_surveyed — All oneOf-with-null constructs are named definitions with descriptions."""
import json
import sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

def is_nullable_oneof(obj):
    """True if obj is a oneOf that mixes null with non-null types."""
    if not isinstance(obj, dict) or 'oneOf' not in obj:
        return False
    branches = obj['oneOf']
    has_null = any(b.get('type') == 'null' for b in branches)
    has_nonnull = any(b.get('type') != 'null' or '$ref' in b for b in branches)
    return has_null and has_nonnull

fails = []

# Named definitions: nullable oneOfs must have a description.
for name, defn in defs.items():
    if is_nullable_oneof(defn):
        if not defn.get('description'):
            fails.append(f'definition {name}: nullable oneOf has no description')

# Properties: inline nullable oneOfs (not via $ref) must have a description.
def check_props(obj, path=''):
    if isinstance(obj, dict):
        if 'properties' in obj:
            for k, v in obj['properties'].items():
                if is_nullable_oneof(v) and not v.get('description'):
                    fails.append(f'{path}/properties/{k}: inline nullable oneOf has no description')
        for k, v in obj.items():
            check_props(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_props(v, f'{path}[{i}]')
check_props({'definitions': defs})

if fails:
    print('FAIL empirical.nullable_fields_surveyed:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS empirical.nullable_fields_surveyed')
