# `rsc/schema/browser-captures/apiConversation/`

JSON Schema (draft-4) for the live claude.ai API conversation format, as returned by
the internal `GET /api/organizations/{org}/chat_conversations/{uuid}` endpoint.

**Input:** individual `.json` files captured by
`src/main/browser-captures/safari_fetch_api_json.sh` — one file per conversation.  
**Schema:** `v1.json` — see `CHANGELOG.md` for coverage.

From the v1.json root description:

> Schema for a single claude.ai conversation as returned by the internal chat API
> (GET /api/organizations/{org}/chat_conversations/{id}). v1 validated against 55 live
> API responses (all pass). See rsc/schema/chat-exports/conversations/ for the bulk-export format.

For full context see [`api-conversation-schema.md`](api-conversation-schema.md)
and [`research.md`](research.md).

---

## Format at a glance

`ApiConversation` is the root type. Messages are in `chat_messages`, discriminated by
`sender` (`human` / `assistant`). Content blocks within each message are discriminated
by `type` (`text`, `thinking`, `tool_use`, `tool_result`).

The format is leaner than the bulk-export format: always-null envelope fields are
absent, citations are present, and tool blocks carry only their active fields.
See `rsc/schema/model_join.csv` for the field-level comparison across all schemas.
