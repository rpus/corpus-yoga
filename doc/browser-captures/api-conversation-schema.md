# `rsc/schema/browser-captures/apiConversation/` — Schema Reference

Schema for the live claude.ai API conversation format, as returned by the internal
`GET /api/organizations/{org}/chat_conversations/{uuid}?tree=true&rendering_mode=messages&render_all_tools=true`
endpoint. See [`doc/README.md`](../README.md) for pipeline context and
[`doc/browser-captures/research.md`](research.md) for how the endpoint was discovered and captured.

---

## What this schema validates

`rsc/schema/browser-captures/apiConversation/v1.json` validates a single JSON file captured from the
live claude.ai API for one conversation. Each file is saved by
`src/main/browser-captures/safari_fetch_api_json.sh` into:

```text
../browser-captures/{export-batch}/{conversation-uuid}/{title}.json
```

This format is **not** the same as the bulk-export format (`conversations.json`).
See [`rsc/schema/model_join.csv`](../model_join.csv) for the field-level comparison.

---

## How it differs from the bulk-export format

| Aspect | Bulk export (`conversations/`) | Live API (`apiConversation/`) |
| --- | --- | --- |
| Source | Periodic export from Settings | Live endpoint, captured via browser |
| Envelope fields | Many always-null UI fields | Stripped — only real data |
| Tool blocks | Full envelope with `flags`, timestamps, `display_content`, etc. | Minimal: `{type, id, name, input}` + active fields only |
| Citations | Absent | Present as `ApiCitation` objects |
| `chat_messages` | Flat array indexed by message UUID | Same structure |
| `account` field | Present | Absent (different auth scope) |
| Versioning | v1–v6 (evolving) | v1 (single snapshot format) |

---

## Top-level structure

`ApiConversation` is the root type. Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `uuid` | UuidV4 | Conversation identifier |
| `name` | string | Conversation title |
| `summary` | string | Auto-generated summary |
| `created_at` | Timestamp | ISO 8601 UTC |
| `updated_at` | Timestamp | ISO 8601 UTC |
| `current_leaf_message_uuid` | UuidV4orV7 | Active branch tip |
| `is_starred` | boolean | User starred |
| `is_temporary` | boolean | Ephemeral conversation |
| `model` | string | Claude model slug, e.g. `"claude-sonnet-4-6"` |
| `platform` | string | e.g. `"CLAUDE_AI"` |
| `settings` | object | Conversation-level feature settings |
| `chat_messages` | array | Ordered message array |

---

## Message types

Each `chat_messages` entry is discriminated by `sender` (via `HasSenderDiscriminatorProperty`):

| `sender` | Type | Notes |
| --- | --- | --- |
| `"human"` | `ApiHumanMessage` | User turn |
| `"assistant"` | `ApiAssistantMessage` | Assistant turn |

Shared base fields (from `ApiMessageBase`): `uuid`, `text`, `content`, `sender`,
`created_at`, `updated_at`, `attachments`, `files`, `parent_message_uuid`, `index`,
`truncated`, `sync_sources`, `stop_reason`, `input_mode`, `chat_feedback`.

---

## Content blocks

`content` arrays are discriminated by `type` (via `HasTypeDiscriminatorProperty`):

| `type` | Schema type | Notes |
| --- | --- | --- |
| `"text"` | `ApiTextBlock` | Text with optional citations; omits `flags` (always null in bulk export) |
| `"thinking"` | `ApiThinkingBlock` | Extended thinking; adds `summaries`, `cut_off`, `truncated` vs bulk export |
| `"tool_use"` | `ApiToolUseBlock` | Union of 17 named tool types |
| `"tool_result"` | `ApiToolResultBlock` | Union of 17 named result types |

### Tool use blocks

All tool use blocks share `ApiToolUseBlockBase` (`type`, `id`, `name`, `input`) via `allOf`.
Named variants cover every tool Claude Code and claude.ai expose:
`Bash`, `Read`, `StrReplace`, `CreateFile`, `View`, `WebSearch`, `WebFetch`,
`ConversationSearch`, `MemoryUserEdits`, `PresentFiles`, `ReadMe`, `RecentChats`,
`RecommendClaudeApps`, `AskUser`, `ToolSearch`, `Visualizer`, `Mcp`.

---

## Validation

Validated against 55 live API responses (all pass). Coverage matrix in
[`rsc/schema/browser-captures/apiConversation/CHANGELOG.md`](../../rsc/schema/browser-captures/apiConversation/CHANGELOG.md).

Run via:

```bash
src/main/browser-captures/RUNME.sh --browser-captures ../browser-captures
```
