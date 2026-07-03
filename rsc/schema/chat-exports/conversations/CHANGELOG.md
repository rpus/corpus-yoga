# conversations schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `gen/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

The API-format variants (`ApiConversation` etc.) live in [`rsc/schema/browser-captures/apiConversation/v1.json`](../ext/browser-captures/apiConversation/v1.json)
and have their own versioning. See [`rsc/schema/browser-captures/apiConversation/`](../ext/browser-captures/apiConversation/) for that schema's history.

---

## v13

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1783005515-45e2d947-batch-0000` (the 2026-07-02 export, 96 conversations). Both drift points were single observations in one conversation; older batches rest at their existing versions.

### Relaxed since v12

- `IntegrationName` — closed enum (plus null) → open `string | null`. The v12 description already warned "likely an open set — do not treat as exhaustive"; a `bash_tool` tool_use with `integration_name: "File Creation"` proved it. This is the `conversations` half of the coupling already applied on the live-API side at apiConversation v7 — missed then because `model_join.csv` had no `IntegrationName` row (added in this cycle, so the next divergence flags both sides).
- `ToolResultBlockBase.start_timestamp` / `stop_timestamp` — `null` → `Timestamp | null`. Real timestamps first observed on `web_search` tool results. The apiConversation side (`ApiToolResultBlockBase`) still pins these to null; it will need the same relaxation (apiConversation v8) when a live capture first exhibits them — not before, since no version may sit ahead of all data.

---

## v12

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1782939670-421f99ee-batch-0000`. The two pre-`hidden` batches fail v12 and rest at their last passing version (v10/v11) in the machine-local matrix — they are *not* dropped. That is the departure from v10: the "every entry passes latest" check was retired (see WORKFLOW.md), so an immutable snapshot may honestly sit below the latest version instead of being forced out.

### Restricted since v11 (material)

claude.ai began emitting `hidden` on every thinking block. Requiring it narrows the accepted set — every export taken before the field shipped lacks it and fails v12. Unlike the analogous `approval_key_legacy` restriction at v10, the pre-field batches are retained in the matrix at v11, recorded as unmodelled by v12 rather than pruned; motivating exactly that retirement.

- `ThinkingBlock` — now requires `hidden: boolean`. Present on all 135 thinking blocks in the new batch; universal in the current export format. Required to match the live-API `ApiThinkingBlock` (apiConversation v6) — the two schemas describe the same thinking blocks, so this is the `conversations` half of the coupling flagged in that v6 note.

### Relaxed since v11

- `RichLink.source` — closed enum → open `string`. The v11 description already warned "likely an open set — do not treat as exhaustive"; the first web_fetch of a new site (`pytorch`) proved it. Now a free string, matching `apiConversation`'s `ApiRichLink.source`, which was already open — restoring agreement between the two coupled schemas rather than diverging.

---

## v11

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1782766739-34e2dc8d-batch-0000`.

### Relaxed since v10

- `ToolResultSearchItem.links` — widened from `null` to `null | array[string]`. `null` remains the normal value — 1268 of 1270 observed search items — but two carried a short list of related URLs (observed in `Career advice part 2`), so the field had been typed `null`-only in error. Same correction as `approval_key` and `ToolResultBlockBase.meta`: a field typed `null` from its always-null samples, later found occasionally populated.

---

## v10

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1782546809-8e17dc80-batch-0000`. Older exports predating `approval_key_legacy` no longer validate and were pruned (retained in the external store).

### Restricted since v9 (material)

The claude.ai bulk export began emitting a new `tool_use` field that v9's closed schema rejects. Requiring it narrows the accepted set — every export before 2026-06-27 lacks it and fails v10 — so the four pre-field exports were dropped, as with the v1→v2 and v2→v3 restrictions.

- `ToolUseBlockBase` — now requires `approval_key_legacy: null`; deprecated/legacy form of `approval_key`, observed always null across the surveyed export (1820/1820). Typed `null` for now (widen to `string | null` if a non-null ever appears, as happened with `approval_key`)

---

## v9

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1781296027-128efb5a-batch-0000`.

### Relaxed since v8

- `TextBlock` — added optional `citations_grouping_mode: string` field; observed value `"combine"`, new claude.ai feature
- `ToolResultBlockBase.meta` — widened from `null` to `null | {output_format_category: string}`; observed values `"md"`, `"none"`, `"other"`
- `Message.content` — removed `minItems: 1`; empty content arrays observed in human messages with no text

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
