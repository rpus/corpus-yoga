# `rsc/schema/claude-code-sessions/`

JSON Schema (draft-4) for Claude Code CLI session transcripts — the `.jsonl` files written
to `~/.claude/projects/{project}/{session}.jsonl` during a Claude Code session.

**Input:** each `.jsonl` converted to a JSON array (one line → one element).  
**Schema:** `v1.json` — see `CHANGELOG.md` for coverage and open questions.

For full context see [`doc/code-sessions-schema.md`](../../../doc/code-sessions-schema.md)
and [`doc/project-overview.md`](../../../doc/project-overview.md).

---

## Format at a glance

Nine record types, discriminated by the top-level `type` field:

| `type` | Description |
| --- | --- |
| `user` | User message turn |
| `assistant` | Assistant message turn |
| `attachment` | File/data attachment accompanying a turn |
| `system` | System event (e.g. turn duration metric) |
| `queue-operation` | Session lifecycle (enqueue / dequeue / popAll / remove) |
| `permission-mode` | Active permission mode at a point in time |
| `last-prompt` | Text and position of the most recent user prompt |
| `file-history-snapshot` | File edit snapshot; links to `~/.claude/file-history/` |
| `ai-title` | AI-generated session title |

User and assistant turns share a **`TurnBase`** envelope (`uuid`, `sessionId`, `timestamp`,
`parentUuid`, `isSidechain`, `cwd`, `gitBranch`, `entrypoint`, `version`, `userType`, `slug`)
and carry a `message` object containing an array of **content blocks**:

| Block `type` | MCP counterpart | Notes |
| --- | --- | --- |
| `text` | `TextContent` | Identical fields |
| `tool_use` | `ToolUseContent` | Identical `id`, `name`, `input`; adds `caller` |
| `tool_result` | `ToolResultContent` | `tool_use_id`/`is_error` are snake_cased equivalents of `toolUseId`/`isError` |
| `thinking` | — | No MCP counterpart; mirrors `ThinkingBlock` in conversations schema |

## `cli_join.csv`

A field-level correspondence table mapping CLI session schema definitions to their
counterparts in the conversations export schema (`../conversations/v6.json`) and the
MCP protocol schema (`../mcp.json`). Columns: `cli_path`, `conv_path`, `mcp_path`,
`relationship`, `note`. Pointer validity is checked by `src/test/pre_commit.py`.

Relationship values mirror `mcp_join.csv`: `identical`, `subset`, `snake_cased`,
`structurally_similar`, `name_collision`, `envelope`, `cli_only`.

---

## Relationship to the conversations schema

This format and the claude.ai export format (`conversations/v*.json`) both wrap the same
Anthropic API content block model. Key differences:

| | CLI sessions | claude.ai export |
| --- | --- | --- |
| Sender convention | `role: user/assistant` | `sender: human/assistant` |
| Envelope | Session mgmt (`parentUuid`, `isSidechain`, `cwd`, `gitBranch`, ...) | UI persistence (`display_content`, `integration_*`, `approval_*`, ...) |
| Tool use `caller` | Present | Absent |
| Thinking blocks | Present | Present (v5+) |
| MCP blocks | Present (namespaced tool names) | Present (v4+) |
