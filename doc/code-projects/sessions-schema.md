# `rsc/schema/sessions/` — Schema Reference

Schema for Claude Code CLI session transcripts. See
[`doc/project-overview.md`](../project-overview.md) for pipeline context,
[`doc/code-projects/research.md`](research.md) for how the format
was reverse-engineered, and
[`rsc/schema/sessions/workflow.md`](../rsc/schema/sessions/workflow.md)
for the validation loop and maintenance lifecycle.

---

## What this schema validates

`rsc/schema/sessions/v1.json` validates a **JSON array** produced by
converting a `~/.claude/projects/{project}/{session}.jsonl` file: each line becomes one
array element.

This format is **not** the same as the claude.ai export format (`conversations.json`).
Both wrap the Anthropic API content block model, but with different envelopes.
See `rsc/schema/sessions/README.md` for the side-by-side comparison.

---

## Nine record types

The top-level `type` field discriminates all records. Four of the nine (`user`,
`assistant`, `attachment`, `system`) share a common **`TurnBase`** envelope.

### Turn envelope (`TurnBase`)

Fields present on `user`, `assistant`, `attachment`, and `system` records:

| Field | Type | Notes |
| --- | --- | --- |
| `uuid` | UuidV4 | Turn identifier |
| `sessionId` | UuidV4 | Session identifier (matches the `.jsonl` filename stem) |
| `timestamp` | Timestamp | ISO 8601 UTC |
| `parentUuid` | UuidV4 \| null | Previous turn; null for the first turn |
| `isSidechain` | boolean | True for subagent conversations; always false in observed exports |
| `entrypoint` | string | `"cli"` or `"claude-vscode"` |
| `version` | string | Claude Code version, e.g. `"2.1.120"` |
| `userType` | string | `"external"` in observed exports |
| `cwd` | string | Working directory at turn time |
| `gitBranch` | string | Active git branch |
| `slug` | string | Human-readable session name, e.g. `"keen-wandering-kite"` |

### `user`

Contains `message: {role: "user", content: [...]}` plus optional fields:

| Field | Notes |
| --- | --- |
| `promptId` | UUID for this prompt submission |
| `permissionMode` | Active permission level (`"default"` observed) |
| `isMeta` | True for internal context injections not shown to the user |
| `isCompactSummary` | True for compaction summary messages |
| `isVisibleInTranscriptOnly` | True when not sent to the API |
| `toolUseResult` | Present when this turn is a tool result fed back into the conversation |
| `sourceToolAssistantUUID` | UUID of the assistant turn whose tool call this responds to |

### `assistant`

Contains `message: {role: "assistant", content: [...]}` plus:

| Field | Notes |
| --- | --- |
| `requestId` | Anthropic API request ID |
| `isApiErrorMessage` | True when this record is an API error |
| `apiErrorStatus` | HTTP status code when `isApiErrorMessage` is true |
| `error` | Error detail object |

### `attachment`

Shares the turn envelope; adds `attachment` (the payload, currently stored as a Python
`repr()` string — an open question in the schema).

### `system`

Shares the turn envelope; adds `subtype` (e.g. `"turn_duration"`), `durationMs`,
`messageCount`, `logicalParentUuid`, `compactMetadata`, `level`.

### `queue-operation`

Session lifecycle record. Fields: `operation` (`enqueue` | `dequeue` | `popAll` | `remove`),
`sessionId`, `timestamp`, optional `content` (prompt text on some enqueue records).

### `permission-mode`

Records: `permissionMode` (`"default"` observed), `sessionId`.

### `last-prompt`

Records: `lastPrompt` (text of the most recent user prompt), `leafUuid` (UUID of the
most recent turn), `sessionId`. Written after each user turn.

### `file-history-snapshot`

Links the session to `~/.claude/file-history/`. Fields: `messageId`, `isSnapshotUpdate`
(false = new snapshot, true = update), optional `snapshot: {messageId, timestamp,
trackedFileBackups}`. The `file-history/` directory stores undo snapshots keyed by a
content hash of the file path — this record is what connects a session UUID to those
snapshots.

### `ai-title`

Fields: `aiTitle` (the generated title string), `sessionId`.

---

## Diagnostic suite

The full diagnostic suite from `src/test/diagnostics/` applies to `v1.json` directly —
the scripts were generalised to derive the BFS root from the schema rather than
hardcoding `Conversation`. All diagnostics pass except `composition.base_schemas_closed`
(justified deviation for `TurnBase`; see `principles.md`). Run via `pre_commit.py`:

```bash
python src/test/pre_commit.py   # section "check_code_projects_diagnostics"
```

---

## `cli_join.csv`

A field-level correspondence table — the CLI sessions equivalent of the conversations
schema's `mcp_join.csv`. Maps each CLI schema definition to its counterpart in both
the conversations export schema (`rsc/schema/conversations/v6.json`) and the MCP protocol schema
(`_reference/mcp.json`). Columns: `cli_path`, `conv_path`, `mcp_path`, `relationship`, `note`.
Pointer validity is enforced by `pre_commit.py`.

Key findings from the table:

- The CLI format is closest to raw MCP at the content block level — `ToolUseBlock`
  fields `id`, `name`, `input` are identical to MCP `ToolUseContent`
- The conversations export adds a heavy UI envelope (timestamps, display_content,
  integration fields, approval fields) absent from both CLI and MCP
- `caller` on `ToolUseBlock` is CLI-only, present in neither MCP nor the export
- `ThinkingBlock` has no MCP counterpart in either format
- `ImageBlock` maps to MCP `ImageContent` but with a different structure (nested
  `source` object vs top-level `data`/`mimeType`); not preserved in claude.ai exports
- `role: user/assistant` (CLI, API convention) vs `sender: human/assistant`
  (conversations export, UI convention) — a name collision at the message level

---

## Content blocks

User and assistant `message.content` arrays contain blocks discriminated by `type`:

| Block type | MCP counterpart | CLI-specific fields |
| --- | --- | --- |
| `text` | `TextContent` | — |
| `tool_use` | `ToolUseContent` | `caller` (no MCP counterpart) |
| `tool_result` | `ToolResultContent` | field names snake_cased vs MCP camelCase |
| `thinking` | — | `thinking`, `signature` |

The `tool_use.name` field distinguishes built-in tools (`Bash`, `Read`, `Edit`, `Write`,
`Agent`) from MCP-namespaced tools (`integration:tool_name`).

---

## Open questions (v1)

- `attachment.attachment` — Python repr string, not JSON. Format unclear.
- `FileHistorySnapshotPayload.trackedFileBackups` — internal structure not surveyed.
- `system.content` — always null in observed exports.
- `Entrypoint` enum — treated as closed on observed values; likely open.
- `TurnBase.userType` — only `"external"` observed.
