# markdownConversation schema changelog

This schema has no machine-local validation matrix: markdownConversation instances are
projections, not captured data — `project_markdown.py` validates each one in-memory at
render time, rather than writing per-datum `vN.log` files under `tmp/cache/`
(see `rsc/schema/WORKFLOW.md`).

---

## v3

### Replaces

v2

#### Relaxed

- `MarkdownConversation.summary` — new **required** property (`string`): the source's
  own summary, which BOTH source shapes always emit (browser-capture
  `apiConversation.summary` and bulk-export `Conversation.summary` — the empty string
  where the backend has not summarised, observed only on the empty stub, which never
  validates anyway), so the projection carries it verbatim and requiring it costs
  nothing — the same argument that made v2 require the message uuid. It is a
  per-snapshot oracle READING — stochastic; the same transcript has been observed to
  re-read differently across snapshots (№99: capture vs export, identical
  `updated_at`) — so it is carried as data, never body-rendered:
  `summaries.py` deposits each distinct reading durably under
  `output/markdown/claude/chat/summaries/` (the memories pattern, per conversation), the
  body's source list links each conversation's deposit index, and `compare_sources`
  reports cross-source summary drift as its own non-gating category.

Also restated at v3 (dressing, not schema): the rendered file opens with YAML
frontmatter — write-time PROVENANCE (source, uuid, turn count, last activity,
cross-check currency vs the other corpus): facts about the file's derivation, not
part of the conversation. The file's outbound LINKS live in the body as a named
SOURCE LIST right after the title — `[This conversation on claude.ai](<url>)` (the
bare `<url>` preamble line retired in its favour) and, in the output/ render,
`[Its distinct summary readings](../summaries/<stem>/index.md)` — proper hyperlinks
with explanatory names, clickable in any markdown renderer, not only the serve
viewer. The rendered body is therefore title + source list + turns.
`strip_frontmatter()` (markdown_projection.py, the format's one authority) removes
the dressing before any cross-source comparison, exactly as `turn_seq` is
anchor-blind. All frontmatter values derive from the local corpora — no wall-clock —
so regeneration stays a no-op when nothing changed (L1).

Refuses thereby: renders predating the field - regenerated at mint, so every current projection validates.

#### Refactored

- `MarkdownConversation` and `MarkdownConversation.summary` descriptions (v3, in place) —
  the summary deposit path re-rooted `output/markdown/…` → `data/output/markdown/…` for the
  four-root migration (#20), which `rsc/schema/` was excluded from sweeping. No validation
  effect. The v3 narrative above and every earlier version keep the path as it stood when
  they were written: their vintage is the record.

## v2

### Replaces

v1

#### Relaxed

- `MarkdownMessage.uuid` — new **required** property (`UuidV4orV7`, definitions copied
  from `apiConversation`): the source message's uuid, the turn's durable identity.
  Present and identical in both source shapes (browser-capture `apiConversation` and
  bulk-export `Conversation` message uuids agree), so requiring it costs nothing and
  the markdown rendering can carry a per-turn HTML anchor (`## Human (3) <a id="<uuid>"></a>`)
  that an index can reference across corpus renumberings — ordinals are presentation,
  uuids are identity.

Validates every current projection (both pipelines re-rendered at mint time).

Refuses thereby: renders predating the field - both pipelines re-rendered at mint time.

## v1

Initial schema: the lean projection shape (`title`, `url`, `messages[{role, content}]`)
that `project_markdown.py` renders to markdown — produced identically from either source
(browser-capture `apiConversation` or bulk-export `Conversation`), which is what puts
cross-source comparison on equal footing.
