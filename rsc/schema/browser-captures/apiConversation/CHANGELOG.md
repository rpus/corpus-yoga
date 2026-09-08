# apiConversation schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

2026-08-24: three inline null-or-string type unions in v10 (ApiToolUseBlockBase's
approval_key and mcp_server_url, ApiToolResultBlockBase's mcp_server_url) were
amended in place to reference the NullableString definition the schema already
holds - the same review catch as conversations v19's signature, applied where
the reviewer found it. No validation effect: no new version. The fresh captures
of 2026-08-24 validate identically before and after.

## v10

Now validates capture 6178046a (2026-08-13, 'The danger of active
negation'), the corpus's first memory write, which failed v1-v9 wholesale
on its one memory message, in three ways: the `memory_user_edits` tool_use
carries `command: "add"` where the enum held only "view"; its result's
display summary is a rich_content item with a subtitles string array and no
url (the past-conversation-link producer carries title and url); and both
blocks carry `tool_origin: "first_party"`, a new envelope field absent from
every other tool block in the live corpus, so it is optional. The
2026-08-17 bulk export renders the same conversation with the same three
deltas - conversations v18, the coupled change, minted in the same cycle;
see model_join.csv.

### Replaces

v9

#### Relaxed

- `ToolInputMemoryUserEdits.command` - the enum gains "add" beside "view": the first observed memory write (the memory text rides in a `control` string, which the open input object already admitted). remove and replace join the enum when a datum exhibits them.
- `ApiToolUseBlockBase.tool_origin` / `ApiToolResultBlockBase.tool_origin` - new OPTIONAL field, enum holding "first_party" only: present on the memory add call and its result, absent from every other observed tool block, so optionality models the corpus and a new value fails loudly.
- `ApiRichContentItem` - items require title only (url is absent on the memory_user_edits producer) and `subtitles` widens from null to null or a string array; past-conversation links keep their observed shape.

#### Refactored

- Schema typing rationalised, 2026-09-08 (reading-room), judged against the
  documenter (`rsc/rpus/documenter.json`) beside the draft-04 meta-schema:
  `ApiHumanMessage` and `ApiAssistantMessage` state `type: object` like every
  other discriminated branch in the house (the wrapper's base already imposed
  it); `NullableString` and `NullableBoolean` spell their union as
  `type: ["null", …]` instead of a `oneOf` of two inline types; `IntegrationName`
  refers to `NullableString` inside a `oneOf` of one instead of restating it. No
  validation effect.

## v9

The 2026-07 claude.ai API adds `thinking_hidden` to live thinking blocks,
beside the existing `hidden`: capture 233aa03f (2026-07-11, 'Persistent self
through alternating agents') is the first datum to carry it and failed v1–v8
wholesale (ApiThinkingBlock is closed). The API stamps the field on EVERY
thinking block it serves (all 4 blocks of the carrying capture), so v9
requires it — a post-introduction block without it is drift and fails
loudly, the ModelId precedent (session v9). The same field surfaced on the
bulk-export side within the same observed window (absent from the
2026-07-08 export, stamped across the whole 2026-07-11 one) —
conversations v16, the coupled change; see model_join.csv.

### Replaces

v8

#### Relaxed

- `ApiThinkingBlock.thinking_hidden` — one NEW REQUIRED field. Observed false only.

Refuses thereby: captures taken before the field appeared (pre-2026-07-11) - re-fetching updates them in place, so the live corpus is uniformly at latest.

## v8

Now validates all 98 captures from the 2026-07-03 re-capture, including the three that failed every prior version. Both changes had been foretold: the first is the API half of a coupling already applied at conversations v13; the second resolves a "no apiConversation counterpart yet" note in `model_join.csv`.

### Replaces

v7

#### Relaxed

- `ApiToolResultBlockBase.start_timestamp` / `stop_timestamp` — `null` → `Timestamp | null`. Real timestamps first observed on `web_search` tool results, in the same conversations that forced the identical relaxation at conversations v13 (the two schemas describe the same underlying blocks). Three captures were affected.
- `ApiToolUseBlockBase.approval_key_legacy` — field added, optional `string` (not nullable: the API has never emitted an explicit null — when unused the field is absent, which optionality already covers). First API observation: a single MCP tool call (of 1,843 surveyed tool_use blocks), carrying a real key string. The bulk-export side is the mirror-opposite: conversations v10+ requires the field and has only ever observed null. A future export will likely force one of two coupled changes there: a real value appears (`null` → `string | null`), or — at least as likely — the always-null emission is dropped in favour of this API shape, tripping the `required` constraint instead (required → optional `string`). Either way, minted only when an export exhibits it.

#### Refactored

- `ApiToolResultSearchItem` description (in place, no validation effect) — its parenthetical claimed `text`/`is_citable`/`prompt_context_metadata` were "always present in bulk-export ToolResultSearchItem"; true only while `web_search` was the shape's sole producer. The 2026-07-05 export carried a metadata-only `web_fetch` knowledge item, conversations v14 relaxed to match this side, and the description now names both producers instead of a stale asymmetry.

---

## v7

Now validates `e545ed1f-21c3-4e76-b355-bd711aa7f388` and any capture with a new integration name.

### Replaces

v6

#### Relaxed

- `IntegrationName` — closed enum → open `string | null`. A fresh capture used the file-creation tool, whose `integration_name` `"File Creation"` was not in the enum. The description already warned "likely an open set — do not treat as exhaustive"; this is the second unlisted value (after the v4/v8 additions), so it was opened to a free string rather than extended again — the same open-set call made for `RichLink.source` at conversations v12. `conversations`' `IntegrationName` is the identical closed enum and will want the same opening when a bulk export carries a new value (coupled).

---

## v6

### Replaces

v5

#### Relaxed

- `ApiThinkingBlock` — added required `hidden: boolean`. claude.ai began emitting this on every thinking block; a fresh browser re-capture found it present on all 135 observed thinking blocks (100%), so it is required, as with `approval_key_legacy` at conversations v10. Captures taken before the field appeared lack it and fail v6 — but re-fetching updates them in place, so the live corpus is uniformly v6. The 14 captures containing thinking blocks consequently drop from v4/v5 to v6 in the (machine-local) matrix.

The `conversations` (bulk-export) `ThinkingBlock` does not yet carry `hidden`; the committed bulk snapshot predates the field. When a fresh bulk export is taken it will need the same addition (coupled with this one).

---

## v5

Now validates `dbd06edd-6293-42a5-aa31-4ef1446ccda1` and any capture with an empty-content message.

### Replaces

v4

#### Relaxed

- `ApiMessageBase.content` — removed `minItems: 1`; empty content arrays observed in messages with no content blocks. `conversations` made the identical relaxation at v9 (`Message.content`); the two schemas describe the same conversation data from different angles, so this restriction had been one-sided.

---

## v4

Validates the current corpus, in which the claude.ai API now emits two root fields it didn't before. v3 and earlier remain the schema for the pre-drift corpus; v4 is the schema for modern captures, which always include these fields.

### Replaces

v3

#### Relaxed

v4 admits the two root fields the live API now includes on every response - v3, closed, refused every capture carrying them. Refuses thereby: a v3-era capture lacking them - re-fetching updates it in place, so every modern capture has them.

- `ApiConversation` — now requires `is_wiggle_enabled: boolean` and `effective_thinking_mode: string`; two root fields the claude.ai API began emitting after v3

#### Refactored

Recorded the observed value sets for the two new fields, surveyed across all 84 captures:

- `is_wiggle_enabled` — always `true` (no `false` observed); description noted
- `effective_thinking_mode` — `"off"` (70), `"auto"` (12), `"extended"` (2); kept as open `string` rather than a closed enum, since claude.ai has a history of adding values (cf. `IntegrationName`)

---

## v3

Now validates `1ded5137`.

### Replaces

v2

#### Relaxed

- `ApiTextBlock` — added optional `citations_grouping_mode: string` field; observed value `"combine"`, new claude.ai feature
- `ApiToolResultBlockBase.meta` — widened from `null` to `null | {output_format_category: string}`; observed values `"md"`, `"none"`, `"other"`

---

## v2

Now validates `9d7817e9`, `b1398a0e`, `c233a466`.

### Replaces

v1

#### Relaxed

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
