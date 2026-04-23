# conversations schema changelog

| Export | v1 | v2 | v3 | v4 | v5 |
| --- | :---: | :---: | :---: | :---: | :---: |
| `data-2026-03-19-22-47-05-batch-0000` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `data-2026-04-03-14-15-13-batch-0000` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `data-2026-04-05-10-33-48-batch-0000` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `data-2026-03-30-14-51-46-batch-0000` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `data-2026-04-07-07-52-05-batch-0000` | ✓ | ✓ | ✗ | ✗ | ✗ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1775902176-0edcf839-batch-0000` | ✗ | ✗ | ✓ | ✓ | ✓ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776351468-ffffb6f7-batch-0000` | ✗ | ✗ | ✗ | ✓ | ✓ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776550128-b9e6a9cd-batch-0000` | ✗ | ✗ | ✗ | ✓ | ✓ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776950570-e265d361-batch-0000` | ✗ | ✗ | ✗ | ✗ | ✓ |

---

## v5

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776950570-e265d361-batch-0000`

### Relaxed since v4

- `ContentBlock.oneOf` — extended with `ThinkingBlock` and its supporting `ThinkingSummary` definition; exports containing extended thinking blocks now pass

---

## v4

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776351468-ffffb6f7-batch-0000`

### Restricted since v3

- `Attachment.file_type` — narrowed from open `string` to enum; instances with unlisted values now fail
- `ToolInputWebSearch.source` — narrowed from open `string` to enum; instances with unlisted values now fail

### Relaxed since v3

- `ToolUseBlock` and `ToolResultBlock` oneOf — extended with `McpToolUseBlock`/`McpToolResultBlock` and `ToolSearchToolUseBlock`/`ToolSearchToolResultBlock`; instances using MCP-namespaced tool names or `tool_search` now pass
- `ToolUseBlockBase.name` and `ToolResultBlockBase.name` — widened from `ToolName` enum to plain `string`; necessary to admit MCP-namespaced names through the base check
- `IntegrationName` — enum extended with `"Claude in Chrome"` and `"Tool Search"`
- `IconName` — enum extended with `"search"`

### Refactored since v3

- `Flags` definition removed; `type: null` inlined at each use site — no validation effect
- `ConversationSearchToolUseBlock.input` — `ToolInputWebSearch` replaced by dedicated `ToolInputConversationSearch` (identical shape: `{query: string}`) — no validation effect

---

## v3

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1775902176-0edcf839-batch-0000`

### Restricted since v2

- `Message.parent_message_uuid` — added as required field; instances lacking it now fail

### Relaxed since v2

- `MessageFile.file_uuid` — added as optional property; instances carrying it now pass (previously rejected by `additionalProperties: false`)
- `DisplayContentCodeBlock.language` — `"text"` added to enum; instances with this value now pass

---

## v2

Now validates `data-2026-03-30-14-51-46-batch-0000`

### Restricted since v1

- `ToolUseBlockBase.mcp_server_url` — added as required field; instances lacking it now fail
- `ToolResultBlockBase.mcp_server_url` — same

---

## v1

Now validates `data-2026-03-19-22-47-05-batch-0000`
