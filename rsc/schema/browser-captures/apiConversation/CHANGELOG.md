# apiConversation schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `gen/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v8

Now validates all 98 captures from the 2026-07-03 re-capture, including the three that failed every prior version. Both changes had been foretold: the first is the API half of a coupling already applied at conversations v13; the second resolves a "no apiConversation counterpart yet" note in `model_join.csv`.

### Relaxed since v7

- `ApiToolResultBlockBase.start_timestamp` / `stop_timestamp` — `null` → `Timestamp | null`. Real timestamps first observed on `web_search` tool results, in the same conversations that forced the identical relaxation at conversations v13 (the two schemas describe the same underlying blocks). Three captures were affected.
- `ApiToolUseBlockBase.approval_key_legacy` — field added, optional `string` (not nullable: the API has never emitted an explicit null — when unused the field is absent, which optionality already covers). First API observation: a single MCP tool call (of 1,843 surveyed tool_use blocks), carrying a real key string. The bulk-export side is the mirror-opposite: conversations v10+ requires the field and has only ever observed null. A future export will likely force one of two coupled changes there: a real value appears (`null` → `string | null`), or — at least as likely — the always-null emission is dropped in favour of this API shape, tripping the `required` constraint instead (required → optional `string`). Either way, minted only when an export exhibits it.

---

## v7

Now validates `e545ed1f-21c3-4e76-b355-bd711aa7f388` and any capture with a new integration name.

### Relaxed since v6

- `IntegrationName` — closed enum → open `string | null`. A fresh capture used the file-creation tool, whose `integration_name` `"File Creation"` was not in the enum. The description already warned "likely an open set — do not treat as exhaustive"; this is the second unlisted value (after the v4/v8 additions), so it was opened to a free string rather than extended again — the same open-set call made for `RichLink.source` at conversations v12. `conversations`' `IntegrationName` is the identical closed enum and will want the same opening when a bulk export carries a new value (coupled).

---

## v6

### Restricted since v5 (material)

- `ApiThinkingBlock` — added required `hidden: boolean`. claude.ai began emitting this on every thinking block; a fresh browser re-capture found it present on all 135 observed thinking blocks (100%), so it is required, as with `approval_key_legacy` at conversations v10. Captures taken before the field appeared lack it and fail v6 — but re-fetching updates them in place, so the live corpus is uniformly v6. The 14 captures containing thinking blocks consequently drop from v4/v5 to v6 in the (machine-local) matrix.

The `conversations` (bulk-export) `ThinkingBlock` does not yet carry `hidden`; the committed bulk snapshot predates the field. When a fresh bulk export is taken it will need the same addition (coupled with this one).

---

## v5

Now validates `dbd06edd-6293-42a5-aa31-4ef1446ccda1` and any capture with an empty-content message.

### Relaxed since v4

- `ApiMessageBase.content` — removed `minItems: 1`; empty content arrays observed in messages with no content blocks. `conversations` made the identical relaxation at v9 (`Message.content`); the two schemas describe the same conversation data from different angles, so this restriction had been one-sided.

---

## v4

Validates the current corpus, in which the claude.ai API now emits two root fields it didn't before. v3 and earlier remain the schema for the pre-drift corpus; v4 is the schema for modern captures, which always include these fields.

### Restricted since v3

Unlike v1–v3 (each a relaxation, accepting a superset of the prior version), v4 *narrows* the accepted set — a v3 document lacking these fields fails v4. This is justified because the live API now includes them on every response, so every modern capture has them.

- `ApiConversation` — now requires `is_wiggle_enabled: boolean` and `effective_thinking_mode: string`; two root fields the claude.ai API began emitting after v3

### Refactored since v3

Recorded the observed value sets for the two new fields, surveyed across all 84 captures:

- `is_wiggle_enabled` — always `true` (no `false` observed); description noted
- `effective_thinking_mode` — `"off"` (70), `"auto"` (12), `"extended"` (2); kept as open `string` rather than a closed enum, since claude.ai has a history of adding values (cf. `IntegrationName`)

---

## v3

Now validates `1ded5137`.

### Relaxed since v2

- `ApiTextBlock` — added optional `citations_grouping_mode: string` field; observed value `"combine"`, new claude.ai feature
- `ApiToolResultBlockBase.meta` — widened from `null` to `null | {output_format_category: string}`; observed values `"md"`, `"none"`, `"other"`

---

## v2

Now validates `9d7817e9`, `b1398a0e`, `c233a466`.

### Relaxed since v1

- `IntegrationName` — opened from closed enum to `string | null`; MCP connector names (e.g. `"GitHub remote MCP server"`) now pass
- `ApiToolUseBlockBase.approval_key` — widened from `null` to `string | null`; observed non-null in MCP tool calls requiring user approval
- `ApiToolUseBlockBase.approval_options` — widened from `null` to `array<string> | null`; observed non-null in MCP tool calls
- `ApiToolUseBlockBase.mcp_server_url` — widened from `null` to `string | null`; observed non-null for connected MCP servers
- `ApiToolResultBlockBase.mcp_server_url` — widened from `null` to `string | null`
- `ApiToolUseBlock.oneOf` and `ApiToolResultBlock.oneOf` — extended with `SearchMcpRegistryToolUseBlock` and `SearchMcpRegistryToolResultBlock`; instances using `search_mcp_registry` now pass
- `ApiTextBlock` — added optional `flags: null` field; observed in `compaction_summary` items
- `ApiMessageBase` — added optional `compaction_summary` field (`array<ApiTextBlock>`); injected by Anthropic when a long conversation is compacted to free context window space

## v1

Initial schema.
