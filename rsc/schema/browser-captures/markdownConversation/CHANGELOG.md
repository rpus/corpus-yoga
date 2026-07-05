# markdownConversation schema changelog

This schema has no machine-local validation matrix: markdownConversation instances are
projections, not captured data — `project_markdown.py` validates each one in-memory at
render time, rather than writing per-datum `vN.log` files under `gen/`
(see `rsc/schema/WORKFLOW.md`).

---

## v2

### Restricted since v1

- `MarkdownMessage.uuid` — new **required** property (`UuidV4orV7`, definitions copied
  from `apiConversation`): the source message's uuid, the turn's durable identity.
  Present and identical in both source shapes (browser-capture `apiConversation` and
  bulk-export `Conversation` message uuids agree), so requiring it costs nothing and
  the markdown rendering can carry a per-turn HTML anchor (`## Human (3) <a id="<uuid>"></a>`)
  that an index can reference across corpus renumberings — ordinals are presentation,
  uuids are identity.

Validates every current projection (both pipelines re-rendered at mint time).

## v1

Initial schema: the lean projection shape (`title`, `url`, `messages[{role, content}]`)
that `project_markdown.py` renders to markdown — produced identically from either source
(browser-capture `apiConversation` or bulk-export `Conversation`), which is what puts
cross-source comparison on equal footing.
