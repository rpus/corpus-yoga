# session schema changelog

<!-- matrix -->
| Session | [v1](./v1.json) | Lines | Bytes (JSONL) |
| --- | :---: | ---: | ---: |
| `Yoga` / `816816d2` | ✓ | 21 | 25,789 |
| `claude-export-yoga` / `a40a0813` | ✓ | 1,409 | 4,555,132 |
| `claude-export-yoga` / `60c07575` | ✓ | 7,522 | 19,585,790 |
| `claude-export-yoga` / `7d59d8ef` | ✓ | 4,850 | 12,387,483 |
| `claude-export-yoga` / `d58db402` | ✓ | 930 | 2,577,519 |
| `claude-export-yoga` / `1bc20fc3` | ✓ | 292 | 1,041,899 |
| `claude-export-yoga` / `a2605476` | ✓ | 402 | 963,806 |
| `claude-export-yoga` / `73f51bc1` | ✓ | 3,594 | 7,606,631 |
| `claude-export-yoga` / `46fcb702` | ✓ | 2,622 | 5,433,869 |
| `claude-export-yoga` / `b0c38f0b` | ✓ | 4,346 | 9,256,629 |
| `nutrition` / `83737fec` | ✓ | 2,843 | 6,489,702 |
| `claude-export-yoga` / `0c66d620` | ✓ | 68 | 277,050 |
| `claude-export-yoga` / `46d179e3` | ✓ | 551 | 1,330,232 |

JSONL byte size is the validation fingerprint — since Claude Code only appends to session
files, the byte count records exactly how much of each session was validated. Lines = records
(one JSON object per line). Project is the bare project name (last path component of `~/.claude/projects/` slug). Schema at validation: `v1.json` at 27,568 bytes.

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
