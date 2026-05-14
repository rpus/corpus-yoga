# `rsc/schema/chat-exports/conversations/` — Schema Reference

This document explains the conversation schema directory: what it validates, how it relates to
the `~/.claude/` local state documented in `rsc/schema/code-projects/session/claude-home-directory.md`, and how the schema
development process works.

For the broader project context (pipeline, artifact recovery, all four schemas, output
structure) see [`project-overview.md`](../README.md).

---

## What this schema is

`rsc/schema/chat-exports/conversations/v6.json` (currently v6) is a JSON Schema (draft-4) that validates
the **claude.ai bulk conversation export format** — the `conversations.json` file you get from:

> Settings → Privacy → Export Data (on claude.ai)

It is **not** a schema for the `~/.claude/projects/*.jsonl` Claude Code CLI session files,
which are a different format. See the [format comparison](#two-conversation-formats) below.

---

## Two conversation formats

Both formats represent "a conversation with Claude" but at different layers and with different
metadata. They share the same underlying **Anthropic API content block model** (`text`,
`tool_use`, `tool_result`) but wrap it differently.

| | **`~/.claude/projects/{session}.jsonl`** | **`conversations.json` (this schema)** |
| --- | --- | --- |
| Source | Claude Code CLI, written live during a session | claude.ai web app, exported on demand |
| Format | JSON Lines — one object per line | JSON array of `Conversation` objects |
| First record | `{"type":"queue-operation","operation":"enqueue",...}` | Top-level `Conversation` with `uuid`, `name`, `summary` |
| Message ID | `parentUuid` + `promptId` (v7 UUIDs) | `uuid` (v7) + `parent_message_uuid` (v4 sentinel or v7) |
| Sender | `role: user/assistant` (API convention) | `sender: human/assistant` (claude.ai UI convention) |
| Envelope fields | `isSidechain`, subagent refs, tool-result spill pointers | `display_content`, `integration_*`, `approval_*`, `is_mcp_app`, `mcp_server_url` |
| Thinking blocks | Present (raw tool-call overhead visible) | Present as `ThinkingBlock` (added in schema v5) |
| MCP tool calls | Full lifecycle: inputs, outputs, subagent orchestration | `McpToolUseBlock` / `McpToolResultBlock` (added in schema v4) |

The core content block types (`TextBlock`, `ToolUseBlock`, `ToolResultBlock`) are structurally
shared — both formats inherit from the same API model. `rsc/schema/model_join.csv` maps
field-by-field correspondences across all pipeline schemas and the MCP protocol spec.

---

## Schema versions

| Version | File | What it added |
| --- | --- | --- |
| v1 | `v1.json` | Initial schema, validates first date-named exports |
| v2 | `v2.json` | `mcp_server_url` required on `ToolUseBlock` / `ToolResultBlock` |
| v3 | `v3.json` | `parent_message_uuid` required; `file_uuid` optional; `"text"` language added |
| v4 | `v4.json` | MCP tool blocks; `ToolSearch` blocks; `McpToolUseBlock` / `McpToolResultBlock` |
| v5 | `v5.json` | `ThinkingBlock` and `ThinkingSummary` (extended thinking) |
| v6 | `v6.json` | `Message.uuid` / `parent_message_uuid` widened to accept v4 or v7 UUIDs |

From v6 onward, versions use **semantic versioning** (`MAJOR.MINOR.PATCH`):

- **MAJOR** — a material restriction; at least one previously-passing export now fails
- **MINOR** — a relaxation or non-material restriction; more exports pass, none fail
- **PATCH** — refactor only; no validation effect

The `CHANGELOG.md` tracks a matrix of which exports pass which schema version.

---

## Supporting files

### `CHANGELOG.md`

Tracks which data exports validate against which schema version. The matrix has one row per
export batch and one column per schema version. This is the ground-truth record of the
schema's coverage.

Export filename formats have changed over time:

- Early: `data-2026-03-19-22-47-05-batch-0000` (timestamp-only)
- Later: `data-{account-uuid}-{unix-timestamp}-{hash}-batch-0000` (account-scoped)

### `principles.md`

A living document of every design rule the schema must follow, with:

- **Status** (`enforced` / `advisory` / `manual` / `informational` / `open`)
- **Diagnostic script path** for enforced rules (run by the pre-commit hook)
- **Repair script path** where repairs are automatable
- **Inline code snippets** for advisory and manual checks

Principles are grouped into eight categories: Naming, Structure, Documentation, Empirical
Grounding, Composition Patterns, API Correspondence, Integrity Constraints, Open Questions.

Key enforced principles:

| Principle | Rule |
| --- | --- |
| `naming.upper_camel_case` | All definition names are UpperCamelCase |
| `structure.bfs_order` | Definitions ordered by breadth-first referential encounter |
| `structure.all_definitions_reachable` | No dead definitions |
| `empirical.validate_against_all_known_exports` | Schema must pass every known export |
| `empirical.oneOf_branches_evidenced` | Every `oneOf` branch seen in at least one export |
| `composition.discriminated_union_pattern` | Unions follow wrapper / base / subtype pattern *(manual — no diagnostic)* |

### `workflow.md`

An 11-step development loop for incorporating new exports or making schema changes:

1. Validate new export against current schema
2. Run all enforced diagnostics
3. Categorise failures by root cause (diagnostic issue vs genuine schema issue)
4. Fix miscalibrated diagnostics before fixing schema
5. Re-run all diagnostics
6. Fix genuine schema issues, one root cause at a time
7. Re-run all diagnostics (expect all pass)
8. Validate against all known exports (expect no regressions)
9. Reissue the schema file
10. Update `principles.md` and `workflow.md`
11. Commit

The workflow enforces a strict ordering: *diagnostics before fixes, categorise before acting,
validate after every change*. The document explicitly instructs collaborators (human or agent)
to flag violations of this ordering rather than silently accommodate them.

### `rsc/schema/model_join.csv`

A unified four-way field correspondence table (conversations ↔ session ↔ apiConversation ↔ MCP).
Columns: `conv_path`, `session_path`, `api_path`, `mcp_path`, `relationship`, `note`.
One row per concept; empty cells where a schema has no counterpart (full outer join semantics).

Relationship values: `identical`, `subset`, `snake_cased`, `structurally_similar`,
`name_collision`, `envelope`, `export_only`, `api_only`, `session_only`, `cli_only`, `null_in_export`.

The key finding: `ContentBlock` is a **name collision** — both schemas use the name but
cover entirely different type sets. The export's `ContentBlock` discriminates on
`text/tool_use/tool_result/thinking`; the MCP `ContentBlock` discriminates on
`text/image/audio/resource_link/resource`.

---

## How this connects to `~/.claude/`

**File-history linkage.** The `~/.claude/file-history/` entries from previous Claude Code
sessions include edits to these schema files. When Claude Code was used to develop the
schema, each edit to `v*.json`, `CHANGELOG.md`, or `principles.md` was captured in
`~/.claude/file-history/{session-uuid}/{path-hash}@v{n}`. The UUID session directories in
`file-history/` are the sessions where this schema work happened.

**`session-report` parallel.** The `session-report` plugin
(`~/.claude/plugins/.../session-report/skills/session-report/`) reads `~/.claude/projects/*.jsonl`
to generate HTML usage reports — exactly the kind of structural analysis this schema does
for claude.ai exports. They are sister tools at different layers: one for CLI sessions, one
for web-app exports.

**Ground truth data.** The `../chat-exports/` sibling directory contains the actual
`conversations.json` export files that the schema is validated against. Those files are not
in this repo — they contain personal conversation content — but the schema development
workflow references them directly via `src/main/chat-exports/validate.sh`.

---

## Empirical grounding

Every constraint in the schema is grounded in observed export data, not assumed. The
`principles.md` document includes diagnostic snippets for surveying any field's observed
values, and the workflow requires that every `oneOf` branch be evidenced in at least one
known export before inclusion. Fields observed as always-null are typed as `"type": "null"`
with a note rather than silently allowed as optional.

This means the schema is a **compressed record of what Claude.ai actually produces**, not
a speculative model of what it might produce.
