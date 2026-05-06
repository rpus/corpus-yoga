# conversations schema changelog

| Export | [v1](./v1.json) | [v2](./v2.json) | [v3](./v3.json) | [v4](./v4.json) | [v5](./v5.json) | [v6](./v6.json) |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| `data-2026-03-19-22-47-05-batch-0000` | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `data-2026-04-03-14-15-13-batch-0000` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| `data-2026-04-05-10-33-48-batch-0000` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| `data-2026-03-30-14-51-46-batch-0000` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| `data-2026-04-07-07-52-05-batch-0000` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1775902176-0edcf839-batch-0000` | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776351468-ffffb6f7-batch-0000` | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776550128-b9e6a9cd-batch-0000` | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776950570-e265d361-batch-0000` | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1777127504-a3d8c71b-batch-0000` | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1777987561-ed936fdf-batch-0000` | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |

The API-format variants (`ApiConversation` etc.) live in [`rsc/schema/apiConversation/v1.json`](../apiConversation/v1.json)
and have their own versioning. See [`rsc/schema/apiConversation/`](../apiConversation/) for that schema's history.

---

## v6

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1777127504-a3d8c71b-batch-0000`

### Relaxed since v5

- `Message.uuid` — widened from `UuidV7` to new `UuidV4orV7`; exports where some message UUIDs are v4 now pass
- `Message.parent_message_uuid` — widened from `ParentMessageUuid` (v5: `oneOf: [UuidV7, NoParentMessageUuidV4]`) to `UuidV4orV7`; exports where some parent message UUIDs are v4 now pass

### Refactored since v5

- `MessageFile.file_uuid` — changed from inline `oneOf: [UuidV4, UuidV7]` to `{$ref: UuidV4orV7}`; semantically equivalent, no validation effect
- `UuidV4` description — updated to document the zero v4 UUID convention
- `UuidV7` description — simplified

---

## v5

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776950570-e265d361-batch-0000`

### Relaxed since v4

- `ContentBlock.oneOf` — extended with `ThinkingBlock` and its supporting `ThinkingSummary` definition; exports containing extended thinking blocks now pass

---

## v4

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776351468-ffffb6f7-batch-0000`

### Restricted since v3 (non-material — no known export uses the restricted values)

- `Attachment.file_type` — narrowed from open `string` to enum
- `ToolInputWebSearch.source` — narrowed from open `string` to enum

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
