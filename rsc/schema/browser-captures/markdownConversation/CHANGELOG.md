# markdownConversation schema changelog

This schema has no machine-local validation matrix: markdownConversation instances are
projections, not captured data — `project_markdown.py` validates each one in-memory at
render time, rather than writing per-datum `vN.log` files under `gen/`
(see `rsc/schema/WORKFLOW.md`).

---

## v1

Initial schema: the lean projection shape (`title`, `url`, `messages[{role, content}]`)
that `project_markdown.py` renders to markdown — produced identically from either source
(browser-capture `apiConversation` or bulk-export `Conversation`), which is what puts
cross-source comparison on equal footing.
