# markdownConversation schema changelog

markdownConversation instances are projections, not captured data. Since v5 the
chat-capture pipeline's validate step lifts each capture into the shape - a claude capture
through `project`, a gemini scrape through `project_scrape`, both in
src/main/markdown_projection.py - and judges it as a family of the pipeline, with a
verdict record and a `v<N>.log` under the datum's `tmp/cache/chat-capture/<provider>/<id>/validation/markdownConversation/`
beside the capture family's; the render step validates the projection in memory as it
always did (see `rsc/schema/WORKFLOW.md`).

---

## v5

The core a claude projection and a gemini scrape share. Gemini's DOM captures are written
in the grammar claude's `render()` emits - the title line, the `<url>` line, `## Human (n)`
and `## Gemini (n)` turns - and `turn_seq` reads both, but no family judged them: the
chat-capture pipeline declared claude/apiConversation alone, every staged gemini unit read
`judged: no family - promoted on its relation alone`, and the reply after `corpus-yoga
browser capture --provider gemini` on reading-room, 2026-10-22, named their promotion with
no rehearsal before it. The family as it stood could not hold a scrape: `summary` and each
turn's `uuid` were required, and a scrape has neither. v5 requires the core alone - the
title, the URL, the turns' roles and text - and keeps the summary and the uuid as the
claude projection's own, so that a scrape lifted by the one parser (`project_scrape`)
validates, and the family moves under the chat-capture pipeline as a family of both its
providers (issues/965).

Validated on reading-room, 2026-10-26: every claude capture's projection and every gemini
scrape of the stage and the corpus validates at v5. v5 drops two requirements and narrows
nothing, so every datum v4 admits, v5 admits.

### Replaces

v4

#### Relaxed

- `MarkdownConversation`: `summary` no longer required.
- `MarkdownMessage`: `uuid` no longer required.
- The family's address: rsc/schema/pipeline/chat-capture/markdownConversation, a family
  of the chat-capture pipeline judging both providers' units.

#### Refactored

- Descriptions name both sources. No validation effect.

## v4

A message's uuid of version 5. Reading-room's browser capture and export of 2026-10-21
carry one assistant message, of 2026-10-14 in conversation `50eea711-…`, whose uuid is
version 5; the projection of that conversation to markdown fails v3 at messages/24/uuid,
the rehearsal of 2026-10-21T204323Z flagging it `INVALID 124-cayley_dickson_construction_identities:
fails markdownConversation`. The uuid union gains `UuidV5` and is renamed
`UuidV4orV5orV7`, in step with apiConversation v14 and conversations v22, minted in the
same cycle, which share the definition by name.

Validated on reading-room, 2026-10-21: v3 refuses the projection at message 24; v4 refuses
none of the 125 staged conversations' projections. v4 adds an alternative and narrows
nothing, so every datum v3 admits, v4 admits.

### Replaces

v3

#### Relaxed

- `UuidV5`, and `UuidV4orV5orV7` in place of `UuidV4orV7` on `MarkdownMessage.uuid` - a
  rename, every reference moved with it.

#### Refactored

- The new definition stands where the BFS repair places it; no earlier definition moved.
  No validation effect.

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
  four-root migration (pull/20), which `rsc/schema/` was excluded from sweeping. No validation
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
