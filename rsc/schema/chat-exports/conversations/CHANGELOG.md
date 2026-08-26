# conversations schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

The API-format variants (`ApiConversation` etc.) live in [`rsc/schema/browser-captures/apiConversation/`](../../browser-captures/apiConversation/)
and have their own versioning. See [`rsc/schema/browser-captures/apiConversation/`](../../browser-captures/apiConversation/) for that schema's history.

---

## v19

Now validates the manifest-era export of 2026-08-24 (the c3cfcf28 export), whose one v18 failure - the record-by-record sweep found exactly one failing block in 118 conversations - is a thinking block of 2026-08-23 carrying signature null with empty thinking and thinking_hidden true.

### Replaces

v18

#### Restricted

None.

#### Relaxed

- ThinkingBlock.signature: string becomes null-or-string - the harness leaves an unsigned blank on an empty hidden block, observed once; every other field of the block unchanged.

#### Refactored

None.

## v18

The 2026-08-13 conversation 6178046a ('The danger of active negation')
carries the corpus's first memory write, and the 2026-08-17 export (epoch
1786967454, batch deb4b507, 116 conversations) failed v1-v17 on exactly that
conversation, in three ways: the `memory_user_edits` tool_use carries
`command: "add"` where the enum held only "view"; its result's display
summary is a rich_content item with a subtitles string array and a null url
(the past-conversation-link producer carries the mirror image); and both
blocks carry `tool_origin: "first_party"`, a new envelope field on 2 of the
export's 3690 tool blocks - the carrying conversation only, so the
serializer does not re-render history with it (the opposite of
`tool_identifier` at v15) and the field is optional. The live capture of
the same conversation exhibits the same three deltas - apiConversation v10,
the coupled change, minted in the same cycle; see model_join.csv. Earlier
batches rest at their versions in the machine-local matrix.

### Replaces

v17

#### Relaxed

- `ToolInputMemoryUserEdits.command` - the enum gains "add" beside "view": the first observed memory write (the memory text rides in a `control` string, which the open input object already admitted). remove and replace join the enum when a datum exhibits them.
- `ToolUseBlockBase.tool_origin` / `ToolResultBlockBase.tool_origin` - new OPTIONAL field, enum holding "first_party" only: present on the memory add call and its result, absent from every other tool block of the export, so optionality models the corpus and a new value fails loudly.
- `RichContentItem` - `subtitles` widens from null to null or a string array, `url` from string to string or null: the memory_user_edits result summary is the shape's second producer (title names the act, subtitles preview the stored text, no chat to point url at); past-conversation links keep their observed shape.

## v17

The 2026-07-22 bulk export adds `hidden_in_chat` to the two tool-block
envelopes: batch 128fd3c8 (export epoch 1784702804, 101 conversations)
failed v1–v16 wholesale (both bases are closed). The serializer stamps the
field on EVERY `tool_use` and `tool_result` block — all 1843 of each,
oldest conversations included — so v17 requires it, the `thinking_hidden`
precedent (v16). Only null observed, so it is typed null: a non-null value
is drift and fails loudly, exactly as this family already treats `flags`,
`context`, and `tool_identifier`. The live API does NOT surface the field:
the same-day browser recapture (2026-07-22, 100 conversations, 43 carrying
tool blocks) shows it in none — bulk-export-only, the `tool_identifier`
precedent (v15), not the `thinking_hidden` coupling (v16); apiConversation
gets the field when a live capture first exhibits it, not before.

### Replaces

v16

#### Relaxed

- `ToolUseBlockBase.hidden_in_chat` — one NEW REQUIRED field. Observed null only.
- `ToolResultBlockBase.hidden_in_chat` — the same field on the result envelope.

Refuses thereby: every export before 2026-07-22, which lacks the field; each rests at its era's version as history (#557).

## v16

The 2026-07 bulk export adds `thinking_hidden` to thinking blocks, beside the
existing `hidden`: batch 6e2b6e2f (export epoch 1783806722) failed v1–v15
wholesale (ThinkingBlock is closed). The export serializer stamps the field
on EVERY thinking block — all 217 in the batch, its oldest conversations
included — so v16 requires it: a post-introduction block without it is drift
and fails loudly, the ModelId precedent (session v9). The live API surfaced the
same field within the same observed window (present on every block of a
2026-07-10 conversation's capture) — apiConversation v9, the coupled
change; see model_join.csv.

### Replaces

v15

#### Relaxed

- `ThinkingBlock.thinking_hidden` — one NEW REQUIRED field. Observed false only.

Refuses thereby: every export before 2026-07-11, which lacks the field; each rests at its era's version as history (#557).

## v15

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1783454107-540c98c0-batch-0000` (the 2026-07-07 export, 100 conversations). One drift point, uniform across the whole corpus: the bulk renderer re-rendered ALL history with one new envelope field — literally the sole difference between this export's and the 2026-07-05 export's rendering of the same March tool block.

### Replaces

v14

#### Relaxed

- `ToolUseBlockBase.tool_identifier` — added as required, null-only (`type: null`, the `context` idiom), following the required-envelope precedent of `mcp_server_url` (v2): present on all 1843 tool_use blocks of this export and null on every one, so instances lacking it now fail — earlier exports rest at v14, per the coverage/frontier doctrine. Absent from the live API captures and from apiConversation as of the same date (bulk-export-only so far), so no coupled api-side mint yet; `model_join.csv` records the pending coupling, and apiConversation gets the field when a live capture first exhibits it — not before, since no version may sit ahead of all data.

## v14

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1783252753-dd1e5d65-batch-0000` (the 2026-07-05 export, 99 conversations). Two drift points, one conversation, one observation each — and both had been foretold: one by the apiConversation side's looser typing (and a description parenthetical claiming the stricter bulk shape held "always"), the other by an explicit either-branch prediction in the apiConversation v8 narrative and `model_join.csv`.

### Replaces

v13

#### Relaxed

- `ToolResultSearchItem.text` — removed from required. The `knowledge` content-item shape gained a second producer: `web_fetch` tool results now carry a metadata-only knowledge item (title, url, webpage metadata, `is_missing` — no `text`, no `is_citable`, no `prompt_context_metadata`), whereas `web_search` items (the shape's only producer through v13) always carry `text`. This converges exactly on the live-API side's `ApiToolResultSearchItem` (apiConversation v8), whose looser required-set already accepted the same block in the same conversation's capture — the coupling `model_join.csv` now records with a direct row (it previously related the two only in prose, the same gap that once let `IntegrationName` diverge silently).
- `ToolUseBlockBase.approval_key_legacy` — `null` → `string | null`. The v8/model_join prophecy resolved on its first branch: a real key string appeared (1 of 1843 tool_use blocks; 1842 null, none absent — so the field stays required), on the very MCP tool call whose live capture had forced the field onto the api side at apiConversation v8. The two sides remain shape-divergent by emission style — the export always emits the field (null when unused), the api emits it only when used — which the updated model_join note now records as the settled state.

## v13

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1783005515-45e2d947-batch-0000` (the 2026-07-02 export, 96 conversations). Both drift points were single observations in one conversation; older batches rest at their existing versions.

### Replaces

v12

#### Relaxed

- `IntegrationName` — closed enum (plus null) → open `string | null`. The v12 description already warned "likely an open set — do not treat as exhaustive"; a `bash_tool` tool_use with `integration_name: "File Creation"` proved it. This is the `conversations` half of the coupling already applied on the live-API side at apiConversation v7 — missed then because `model_join.csv` had no `IntegrationName` row (added in this cycle, so the next divergence flags both sides).
- `ToolResultBlockBase.start_timestamp` / `stop_timestamp` — `null` → `Timestamp | null`. Real timestamps first observed on `web_search` tool results. The apiConversation side (`ApiToolResultBlockBase`) still pins these to null; it will need the same relaxation (apiConversation v8) when a live capture first exhibits them — not before, since no version may sit ahead of all data.

#### Refactored

- `RichLink.source` description (in v12 and v13, in place) — example site names generalised to "a site/publication slug": narratives and current schema descriptions are data-anonymised now that the user-specific matrices live outside the repo. No validation effect. (The closed site enums in v11 and earlier are validating and remain untouched.)

---

## v12

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1782939670-421f99ee-batch-0000`. The two pre-`hidden` batches fail v12 and rest at their last passing version (v10/v11) in the machine-local matrix — they are *not* dropped. That is the departure from v10: the "every entry passes latest" check was retired (see WORKFLOW.md), so an immutable snapshot may honestly sit below the latest version instead of being forced out.

### Replaces

v11

#### Relaxed

claude.ai began emitting `hidden` on every thinking block, and v12 admits it - v11, closed, refused every export carrying it. Refuses thereby: every export taken before the field shipped, which lacks it. Unlike the analogous `approval_key_legacy` restriction at v10, the pre-field batches are retained in the matrix at v11, recorded as unmodelled by v12 rather than pruned; motivating exactly that retirement.

- `ThinkingBlock` — now requires `hidden: boolean`. Present on all 135 thinking blocks in the new batch; universal in the current export format. Required to match the live-API `ApiThinkingBlock` (apiConversation v6) — the two schemas describe the same thinking blocks, so this is the `conversations` half of the coupling flagged in that v6 note.

- `RichLink.source` — closed enum → open `string`. The v11 description already warned "likely an open set — do not treat as exhaustive"; the first web_fetch of a previously-unseen site proved it. Now a free string, matching `apiConversation`'s `ApiRichLink.source`, which was already open — restoring agreement between the two coupled schemas rather than diverging.

---

## v11

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1782766739-34e2dc8d-batch-0000`.

### Replaces

v10

#### Relaxed

- `ToolResultSearchItem.links` — widened from `null` to `null | array[string]`. `null` remains the normal value — 1268 of 1270 observed search items — but two carried a short list of related URLs (observed in conversation `057271b2`), so the field had been typed `null`-only in error. Same correction as `approval_key` and `ToolResultBlockBase.meta`: a field typed `null` from its always-null samples, later found occasionally populated.

---

## v10

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1782546809-8e17dc80-batch-0000`. Older exports predating `approval_key_legacy` no longer validate and were pruned (retained in the external store).

### Replaces

v9

#### Relaxed

The claude.ai bulk export began emitting a new `tool_use` field that v9's closed schema rejected; v10 admits it. Refuses thereby: every export before 2026-06-27, which lacks it - the four pre-field exports were dropped at the time, as at v1→v2 and v2→v3.

- `ToolUseBlockBase` — now requires `approval_key_legacy: null`; deprecated/legacy form of `approval_key`, observed always null across the surveyed export (1820/1820). Typed `null` for now (widen to `string | null` if a non-null ever appears, as happened with `approval_key`)

---

## v9

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1781296027-128efb5a-batch-0000`.

### Replaces

v8

#### Relaxed

- `TextBlock` — added optional `citations_grouping_mode: string` field; observed value `"combine"`, new claude.ai feature
- `ToolResultBlockBase.meta` — widened from `null` to `null | {output_format_category: string}`; observed values `"md"`, `"none"`, `"other"`
- `Message.content` — removed `minItems: 1`; empty content arrays observed in human messages with no text

---

## v8

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1779222449-06d73759-batch-0000`.

### Replaces

v7

#### Relaxed

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

### Replaces

v6

#### Refactored

- Extracted the root array type into a `Conversations` definition (`"type": "array", "minItems": 1, "items": {"$ref": "#/definitions/Conversation"}`), making the root consistent with every other top-level type in the schema (which use the `allOf` + `$ref` wrapper pattern). No change to validation behaviour — all exports that pass v6 pass v7 and vice versa.

---

## v6

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1777127504-a3d8c71b-batch-0000`

### Replaces

v5

#### Relaxed

- `Message.uuid` — widened from `UuidV7` to new `UuidV4orV7`; exports where some message UUIDs are v4 now pass
- `Message.parent_message_uuid` — widened from `ParentMessageUuid` (v5: `oneOf: [UuidV7, NoParentMessageUuidV4]`) to `UuidV4orV7`; exports where some parent message UUIDs are v4 now pass

#### Refactored

- `MessageFile.file_uuid` — changed from inline `oneOf: [UuidV4, UuidV7]` to `{$ref: UuidV4orV7}`; semantically equivalent, no validation effect
- `UuidV4` description — updated to document the zero v4 UUID convention
- `UuidV7` description — simplified

---

## v5

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776950570-e265d361-batch-0000`

### Replaces

v4

#### Relaxed

- `ContentBlock.oneOf` — extended with `ThinkingBlock` and its supporting `ThinkingSummary` definition; exports containing extended thinking blocks now pass

---

## v4

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776351468-ffffb6f7-batch-0000`

### Replaces

v3

#### Restricted (non-material — no known export uses the restricted values)

- `Attachment.file_type` — narrowed from open `string` to enum
- `ToolInputWebSearch.source` — narrowed from open `string` to enum

#### Relaxed

- `ToolUseBlock` and `ToolResultBlock` oneOf — extended with `McpToolUseBlock`/`McpToolResultBlock` and `ToolSearchToolUseBlock`/`ToolSearchToolResultBlock`; instances using MCP-namespaced tool names or `tool_search` now pass
- `ToolUseBlockBase.name` and `ToolResultBlockBase.name` — widened from `ToolName` enum to plain `string`; necessary to admit MCP-namespaced names through the base check
- `IntegrationName` — enum extended with `"Claude in Chrome"` and `"Tool Search"`
- `IconName` — enum extended with `"search"`

#### Refactored

- `Flags` definition removed; `type: null` inlined at each use site — no validation effect
- `ConversationSearchToolUseBlock.input` — `ToolInputWebSearch` replaced by dedicated `ToolInputConversationSearch` (identical shape: `{query: string}`) — no validation effect

---

## v3

Now validates `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1775902176-0edcf839-batch-0000`

### Replaces

v2

#### Relaxed

- `Message.parent_message_uuid` — added as required field; instances lacking it now fail

- `MessageFile.file_uuid` — added as optional property; instances carrying it now pass (previously rejected by `additionalProperties: false`)
- `DisplayContentCodeBlock.language` — `"text"` added to enum; instances with this value now pass

---

## v2

Now validates `data-2026-03-30-14-51-46-batch-0000`

### Replaces

v1

#### Relaxed

- `ToolUseBlockBase.mcp_server_url` — added as required field; instances lacking it now fail
- `ToolResultBlockBase.mcp_server_url` — same

---

## v1

Now validates `data-2026-03-19-22-47-05-batch-0000`
