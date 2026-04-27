#!/usr/bin/env python
"""documentation.open_set_enums_documented — Likely open-set enums say so in their description."""
import json, sys

# Enum value sets that are genuinely closed (exhaustive by design).
# Each entry is annotated with the schema version from which it applies.
KNOWN_CLOSED = {
    frozenset(['human', 'assistant']),                             # conversations v1+: Message.sender
    frozenset(['enqueue', 'dequeue', 'popAll', 'remove']),         # sessions v1+: QueueOperationName
    frozenset(['cli', 'claude-vscode']),                           # sessions v1+: Entrypoint
}

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

fails = []
for defn_name, defn in defs.items():
    defn_desc = defn.get('description', '')
    defn_open = 'open set' in defn_desc or 'exhaustive' in defn_desc
    def check(obj, path=''):
        if isinstance(obj, dict):
            if 'enum' in obj and len(obj['enum']) > 1:
                vals = frozenset(obj['enum'])
                local_desc = obj.get('description', '')
                local_ok = ('open set' in local_desc or 'exhaustive' in local_desc
                            or 'discriminator' in local_desc)
                if vals not in KNOWN_CLOSED and not defn_open and not local_ok:
                    fails.append(f'{defn_name}{path}')
            for k, v in obj.items(): check(v, f'/{k}')
        elif isinstance(obj, list):
            for i, v in enumerate(obj): check(v, f'[{i}]')
    check(defn)

if fails:
    print('FAIL documentation.open_set_enums_documented:')
    for f in fails: print(f'  {f}')
    sys.exit(1)
print('PASS documentation.open_set_enums_documented')
