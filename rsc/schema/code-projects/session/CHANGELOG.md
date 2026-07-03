# session schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `gen/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v4

### Relaxed since v3

- `ModeRecord` — new record type (`type: "mode"`) with required `mode: string` and `sessionId: UuidV4`. Observed with `mode: "normal"`. Written alongside other session lifecycle records. Sessions `83737fec` and `57289774` now pass; they fail v1–v3. Sessions `89515719` and `df71fdce` originally passed v1–v3 (registered before they emitted a `mode` record); both have since grown to include one, so they now fail v1–v3 and pass only v4 — the same transition, observed live.

---

## v3

### Relaxed

- Added `DocumentBlock` content block type (`type: "document"`) to `ContentBlock.oneOf`. Observed when Claude Code passes a file as context to the model. Block shape: `{type, source: {type, media_type, data}, title}`. All observed instances have `source.type: "text"` and `source.media_type: "text/plain"`. Session `32bd7448` now passes; it fails v1 and v2.

### Refactored (description only)

- `AiTitleRecord.description`: corrected "Written once early in the session" to reflect observed behaviour — written repeatedly throughout the session (~299 times in a 4868-record session), appearing to be a heartbeat rather than a one-time write. No validation change.
- `AiTitleRecord.description`: further updated to reflect that the title is also set by user rename via the VS Code UI — all sources write the same record type with no distinguishing field; last record wins (`currentSessionTitle`).
- `AiTitleRecord.properties.aiTitle.description`: clarified that despite the field name the value is not exclusively AI-generated; also set by user rename. Last-wins semantics.

---

## v2

### Refactored

- Extracted the root array type into a `Session` definition (`"type": "array", "minItems": 1, "items": {"$ref": "#/definitions/Record"}`), making the root consistent with every other top-level type in the schema (which use the `allOf` + `$ref` wrapper pattern). No change to validation behaviour — all sessions that pass v1 pass v2 and vice versa.

---

## v1

Initial schema. Validated against two Claude Code sessions from the
`claude-export-yoga` project.

### Record types

| Type | `additionalProperties` | Notes |
| --- | --- | --- |
| `user` | open (composition) | |
| `assistant` | open (composition) | |
| `attachment` | open (composition) | |
| `system` | open (composition) | |
| `queue-operation` | closed | |
| `permission-mode` | closed | |
| `last-prompt` | closed | `leafUuid` optional — absent in some observed records |
| `file-history-snapshot` | closed | |
| `ai-title` | closed | |

Turn-like records (`user`, `assistant`, `attachment`, `system`) share a `TurnBase`
envelope via `allOf`. `TurnBase` is intentionally open (`additionalProperties` absent)
because in draft-4, `additionalProperties` on a base schema used in `allOf` does not
see properties defined in sibling schemas — closing it would incorrectly reject the
type-specific fields added by each subtype.

### Content block types

| Type | `additionalProperties` | MCP counterpart |
| --- | --- | --- |
| `text` | closed | `TextContent` |
| `tool_use` | closed | `ToolUseContent` (adds `caller`) |
| `tool_result` | closed | `ToolResultContent` (snake_cased fields) |
| `thinking` | closed | — |
| `image` | closed | `ImageContent` (different structure) |

### AssistantMessage fields discovered during validation

`AssistantMessage` has `additionalProperties: false`. The following fields were
discovered iteratively by running `src/main/code-projects/RUNME.sh` and re-tightening:

| Field | Type | Notes |
| --- | --- | --- |
| `stop_sequence` | `["null", "string"]` | Empty string observed on rate-limit responses |
| `diagnostics` | `["null", "object"]` | Cache miss reason and similar metadata |
| `context_management` | `["null", "object"]` | `{applied_edits: [...]}` when context was managed |
| `container` | `"null"` | Always null in observed exports |

### Multi-type fields

Fields that are genuinely polymorphic across observed records, typed with `type` arrays:

| Field | Type | Observed values |
| --- | --- | --- |
| `UserTurnType.toolUseResult` | `["string", "object"]` | Rejection message string; object form not yet sampled |
| `AssistantTurnType.error` | `["string", "object"]` | `"rate_limit"` string; object form not yet sampled |
| `AttachmentRecordType.attachment` | `["string", "object"]` | JSON object (`deferred_tools_delta`); Python repr string in older exports |
| `SystemRecordType.content` | `["null", "string"]` | Null for `turn_duration`; `"Conversation compacted"` for `compact_boundary` |
| `ToolResultBlock.content` | `["string", "array"]` | Plain string (common); array of text blocks for richer results |
| `AssistantMessage.stop_reason` | `["null", "string"]` | Null mid-stream; `"tool_use"`, `"stop_sequence"` etc. when complete |
| `AssistantMessage.stop_sequence` | `["null", "string"]` | Null or empty string |
| `AssistantMessage.context_management` | `["null", "object"]` | See above |
| `AssistantMessage.diagnostics` | `["null", "object"]` | See above |

### Open questions

- `AttachmentRecordType.attachment` — Python repr string form not yet confirmed in current
  exports; only JSON object form observed. The repr form may be from older Claude Code versions.
- `FileHistorySnapshotPayload.trackedFileBackups` — internal structure not yet surveyed.
- `Entrypoint` enum — `cli` and `claude-vscode` observed; treated as closed pending further exports.
- `TurnBase.userType` — only `"external"` observed; presumably `"internal"` exists.
- `UserTurnType.toolUseResult` object form — string form observed; object form documented but not sampled.
- `AssistantTurnType.error` object form — string form observed; object form documented but not sampled.
