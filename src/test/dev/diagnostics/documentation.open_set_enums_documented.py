#!/usr/bin/env python
"""documentation.open_set_enums_documented — Likely open-set enums say so in their description."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/test/dev - the diagnostics' shared walk
from schema_walk import schema_nodes  # noqa: E402

# Enum value sets that are genuinely closed (exhaustive by design).
# Each entry is annotated with the schema version from which it applies.
KNOWN_CLOSED = {
    frozenset(['human', 'assistant']),                             # conversations v1+: Message.sender
    frozenset(['enqueue', 'dequeue', 'popAll', 'remove']),         # session v1+: QueueOperationName
    frozenset(['cli', 'claude-vscode']),                           # session v1+: Entrypoint
}

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

fails = []
for defn_name, defn in defs.items():
    defn_desc = defn.get('description', '')
    defn_open = 'open set' in defn_desc or 'exhaustive' in defn_desc
    for path, node in schema_nodes(defn, f'#/definitions/{defn_name}'):
        if isinstance(node.get('enum'), list) and len(node['enum']) > 1:
            vals = frozenset(node['enum'])
            local_desc = node.get('description', '')
            local_ok = ('open set' in local_desc or 'exhaustive' in local_desc
                        or 'discriminator' in local_desc)
            if vals not in KNOWN_CLOSED and not defn_open and not local_ok:
                fails.append(path)

if fails:
    print('FAIL documentation.open_set_enums_documented:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS documentation.open_set_enums_documented')
