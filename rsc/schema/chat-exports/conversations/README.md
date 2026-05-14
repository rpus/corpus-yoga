# `rsc/schema/chat-exports/conversations/`

These schemas validate the **claude.ai web-app export format**, not the
`~/.claude/projects/*.jsonl` Claude Code CLI format. Both represent Claude conversations
but differ structurally in what they capture.

From the v6.json root description:

> Schema for the Claude.ai bulk conversation export format (`conversations.json`), obtained
> via Settings → Privacy → Export Data.

For a full explanation of the schema directory — versioning, supporting files, development
workflow, and MCP correspondence — see [`conversations-schema.md`](conversations-schema.md).

---

## Two conversation formats

| | `~/.claude/projects/{session}.jsonl` | `conversations.json` (this schema) |
| --- | --- | --- |
| Source | Claude Code CLI, written live during a session | claude.ai web app, exported on demand |
| Format | JSON Lines — one object per line | JSON array of `Conversation` objects |
| First record | `{"type":"queue-operation","operation":"enqueue",...}` | Top-level `Conversation` with `uuid`, `name`, `summary` |
| Message ID | `parentUuid` / `promptId` (v7 UUIDs) | `uuid` (v7), `parent_message_uuid` (v4 sentinel or v7) |
| Sender | `role: user/assistant` (API convention) | `sender: human/assistant` (claude.ai UI convention) |
| Envelope | `isSidechain`, subagent refs, tool-result spill pointers | `display_content`, `integration_*`, `approval_*`, `is_mcp_app` |
| Thinking blocks | Present (raw tool-call overhead visible) | Present as `ThinkingBlock` (added in schema v5) |
| MCP | Full tool call lifecycle | `McpToolUseBlock` / `McpToolResultBlock` (added in schema v4) |

Both wrap the same Anthropic API content block model (`text`, `tool_use`, `tool_result`).
`rsc/schema/model_join.csv` maps the exact field-level correspondences across all pipeline
schemas and the MCP protocol spec.

---

## How the two formats are connected

**File-history.** `~/.claude/file-history/` captures every file edited during a Claude Code
session. The UUID session directories in that store include sessions where these schema files
were developed — so edits to `CHANGELOG.md`, `v*.json`, and `principles.md` are all
snapshotted there.

**`session-report`.** The `session-report` plugin reads `~/.claude/projects/*.jsonl` to
generate HTML usage reports — the same kind of structural analysis that these schemas do for
claude.ai exports, but at the CLI layer rather than the web-app layer.

**Ground-truth data.** The `../../chat-exports/` sibling directory (outside this repo)
contains the actual `conversations.json` export files that the schemas are validated against.
