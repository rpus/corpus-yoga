# conversations schema changelog

<!-- matrix -->
| Export | [v1](./v1.json) | [v2](./v2.json) | [v3](./v3.json) | [v4](./v4.json) | [v5](./v5.json) | [v6](./v6.json) | [v7](./v7.json) | [v8](./v8.json) | Bytes |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1779222449-06d73759-batch-0000` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | 24,648,484 |

Bytes: size of the conversations JSON file at validation time.

---

The API-format variants (`ApiConversation` etc.) live in [`rsc/schema/browser-captures/apiConversation/v1.json`](../ext/browser-captures/apiConversation/v1.json)
and have their own versioning. See [`rsc/schema/browser-captures/apiConversation/`](../ext/browser-captures/apiConversation/) for that schema's history.

---

## v8

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1779222449-06d73759-batch-0000`.

### Relaxed since v7

- `IntegrationName` — opened from closed enum to `string | null`; MCP connector names (e.g. `"GitHub remote MCP server"`) now pass
- `ToolUseBlockBase.approval_key` — widened from `null` to `string | null`; observed non-null in MCP tool calls requiring user approval
- `ToolUseBlockBase.approval_options` — widened from `null` to `array<string> | null`; observed non-null in MCP tool calls
- `ToolUseBlockBase.mcp_server_url` — widened from `null` to `string | null`; observed non-null for connected MCP servers
- `ToolResultBlockBase.mcp_server_url` — widened from `null` to `string | null`
- `ToolUseBlock.oneOf` and `ToolResultBlock.oneOf` — extended with `SearchMcpRegistryToolUseBlock` and `SearchMcpRegistryToolResultBlock`; instances using `search_mcp_registry` now pass
- `ToolResultSearchItem.is_citable` and `ToolResultSearchItem.prompt_context_metadata` — removed from required; absent in some web search results
- `ToolResultSearchItem` — added optional `links: null` field

---

## v7

### Refactored since v6

- Extracted the root array type into a `Conversations` definition (`"type": "array", "minItems": 1, "items": {"$ref": "#/definitions/Conversation"}`), making the root consistent with every other top-level type in the schema (which use the `allOf` + `$ref` wrapper pattern). No change to validation behaviour — all exports that pass v6 pass v7 and vice versa.

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
