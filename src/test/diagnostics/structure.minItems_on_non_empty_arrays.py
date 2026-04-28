#!/usr/bin/env python
"""structure.minItems_on_non_empty_arrays — Non-empty arrays have minItems: 1."""
import json
import sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

checks = [
    ('root array', schema),
    ('chat_messages', defs.get('Conversation', {}).get('properties', {}).get('chat_messages', {})),
    ('content',      defs.get('Message', {}).get('properties', {}).get('content', {})),
]
fails = [label for label, obj in checks
         if obj.get('type') == 'array' and obj.get('minItems', 0) < 1]

if fails:
    print(f'FAIL structure.minItems_on_non_empty_arrays: {fails}')
    sys.exit(1)
print('PASS structure.minItems_on_non_empty_arrays')
