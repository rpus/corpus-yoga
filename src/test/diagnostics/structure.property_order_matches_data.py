#!/usr/bin/env python
"""structure.property_order_matches_data — Property order in schema matches observed field order in data."""
import json, sys

with open(sys.argv[1]) as f:
    schema = json.load(f)
defs = schema.get('definitions', {})

# Canonical field orders empirically derived from export data.
# Only the fields present in each definition's properties are checked;
# definitions may omit trailing optional fields without violating the order.
CANONICAL = {
    'Conversation':       ['uuid', 'name', 'summary', 'created_at', 'updated_at', 'account', 'chat_messages'],
    'Message':            ['uuid', 'text', 'content', 'sender', 'created_at', 'updated_at',
                           'attachments', 'files', 'parent_message_uuid'],
    'TextBlock':          ['type', 'start_timestamp', 'stop_timestamp', 'text', 'citations', 'flags'],
    'ToolUseBlockBase':   ['type', 'start_timestamp', 'stop_timestamp', 'flags', 'id', 'name', 'input',
                           'message', 'integration_name', 'integration_icon_url', 'icon_name',
                           'context', 'approval_options', 'approval_key', 'is_mcp_app', 'mcp_server_url',
                           'display_content'],
    'ToolResultBlockBase': ['type', 'start_timestamp', 'stop_timestamp', 'flags', 'tool_use_id', 'name',
                            'content', 'is_error', 'structured_content', 'meta', 'message',
                            'integration_name', 'mcp_server_url', 'integration_icon_url', 'icon_name',
                            'display_content'],
}

fails = []
for defn_name, canonical in CANONICAL.items():
    if defn_name not in defs:
        continue
    actual = list(defs[defn_name].get('properties', {}).keys())
    # Build relative-order check: for each pair in canonical, their relative order in actual must agree.
    pos = {k: i for i, k in enumerate(actual)}
    for i, a in enumerate(canonical):
        for b in canonical[i + 1:]:
            if a in pos and b in pos and pos[a] > pos[b]:
                fails.append(f'{defn_name}: "{a}" appears after "{b}" (expected before)')

if fails:
    print('FAIL structure.property_order_matches_data:')
    for f in fails:
        print(f'  {f}')
    sys.exit(1)
print('PASS structure.property_order_matches_data')
