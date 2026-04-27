#!/usr/bin/env python
"""composition.discriminated_union_pattern — Structural oneOf unions have Has*DiscriminatorProperty in allOf."""
import json, sys

# oneOf unions that are correct but do not follow the discriminated-union pattern
# because they discriminate on key-presence or are primitive-type unions rather
# than object unions with a type/name field discriminator.
# Each entry is annotated with the schema version from which it applies.
KNOWN_NON_DISCRIMINATED_UNIONS = {
    '/definitions/ToolResultSearchItem/properties/prompt_context_metadata',  # conversations v1+: key-presence (search vs fetch)
    '/definitions/MessageFile/properties/file_uuid',                          # conversations v3+: key-presence (with vs without uuid)
    '/definitions/UuidV4orV7',                                                # conversations v6+: primitive union UuidV4|UuidV7
    '/definitions/TurnBase/properties/parentUuid',                            # claude-code-sessions v1+: nullable primitive (null|UuidV4)
}

with open(sys.argv[1]) as f:
    schema = json.load(f)

fails = []
def check(obj, path=''):
    if isinstance(obj, dict):
        if ('oneOf' in obj
                and any('$ref' in b for b in obj['oneOf'])
                and path not in KNOWN_NON_DISCRIMINATED_UNIONS):
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
