#!/usr/bin/env python3
"""composition.discriminated_union_pattern — Structural oneOf unions have Has*DiscriminatorProperty in allOf."""
import json, sys

KNOWN_KEY_PRESENCE = {
    '/definitions/ToolResultSearchItem/properties/prompt_context_metadata',
    '/definitions/MessageFile/properties/file_uuid',
    '/definitions/ParentMessageUuid',
}

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if ('oneOf' in obj
                and any('$ref' in b for b in obj['oneOf'])
                and path not in KNOWN_KEY_PRESENCE):
            all_of_refs = [s.get('$ref', '') for s in obj.get('allOf', [])]
            if not any('DiscriminatorProperty' in r for r in all_of_refs):
                fails.append(path)
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)

if fails:
    print('FAIL composition.discriminated_union_pattern:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS composition.discriminated_union_pattern')
