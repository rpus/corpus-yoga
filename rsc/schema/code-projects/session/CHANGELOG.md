# session schema changelog

<!-- matrix -->
| Code project | [v1](./v1.json) | [v2](./v2.json) | [v3](./v3.json) | Bytes | Session UUID |
| --- | :---: | :---: | :---: | ---: | --- |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 4,556,544 | `a40a0813-8a53-4503-a2ca-0b52b95e6406` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 19,593,315 | `60c07575-359d-4484-aaa1-6068f03d5297` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 12,392,336 | `7d59d8ef-0ccb-4ffa-8bd5-12c157ec9492` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 2,578,452 | `d58db402-6597-4f96-a2c7-ba3da7ac5bf5` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 1,042,194 | `1bc20fc3-edf2-46fd-89db-b5481f112ef0` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 964,211 | `a2605476-5569-4640-8386-cf7f466578ae` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 9,075,761 | `73f51bc1-229b-413f-9907-8376b4e6e9c2` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 5,436,494 | `46fcb702-d196-4bc2-a67c-2efc3febac11` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 9,260,978 | `b0c38f0b-0ae9-4134-bedb-56b03ce63407` |
| `-dev-Anthropic-nutrition` | ✓ | ✓ | ✓ | 6,492,548 | `83737fec-e5c3-4ce8-b2d9-6f05fe7a9ee2` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 277,617 | `0c66d620-7e5f-40d6-a387-0731d9aaab0a` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 1,610,584 | `46d179e3-bdc5-4633-b5d0-81c1328c4f3d` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 801,392 | `a1fe23f6-c5ea-425d-b503-775edb797bc3` |
| `-dev-Anthropic-claude-export-yoga` | ✗ | ✗ | ✓ | 12,065,984 | `32bd7448-f34b-4576-bbf8-a28a88275b73` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 5,265,747 | `e87e0735-5bf3-484c-b60d-8761ea8decab` |
| `-dev-Anthropic-claude-export-yoga` | ✓ | ✓ | ✓ | 4,451,058 | `68ae3555-cf35-4e4f-926d-a390d03589e9` |
| `-dev-github-rpus-claude-export-yoga` | ✓ | ✓ | ✓ | 8,039,412 | `d91fa43e-e7a0-4cb9-b24f-6163ef7bba96` |
| `-dev-github-rpus-claude-export-yoga` | ✓ | ✓ | ✓ | 7,223,947 | `c7639338-2b81-47fb-9136-2fd879eaec04` |
| `-dev-github-rpus-claude-export-yoga` | ✓ | ✓ | ✓ | 663,370 | `d8234533-ad49-42e7-967f-db33a0373a51` |

Bytes: size of the session JSON file at validation time.

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
