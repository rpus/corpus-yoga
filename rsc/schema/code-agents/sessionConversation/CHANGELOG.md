# sessionConversation schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `gen/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v1

Inaugural version, minted 2026-07-11 from the six local sessions (two projects).
The family models a session read as TALK: `project_conversation.py` projects each
converted session (`session.json`, the `session` family's datum) to a
`conversation.json` beside it — user and assistant records only (no sidechains,
no meta records, no tool-result carriers), each reduced to its visible text; a
record whose projection is empty contributes no turn. Roles use the corpus
vocabulary (`human`/`assistant`, matching `browser-captures/markdownConversation`)
because this shape is the projection source for the session corpus render under
`lib/markdown/code/conversations/`.

Evidence notes:

- `title` — every observed local session carries an ai-title; `''` is reachable
  by construction (a session never titled) and legal.
- `messages` — non-empty in all six observed sessions; empty is reachable by
  construction (a session that is all tool work) and legal, so no `minItems`.
- `Message.content` — `minLength: 1` by construction: an empty projection
  contributes no turn at all.
- `created` / `last_activity` — ISO 8601 with milliseconds and `Z` in every
  observed record; carried as plain strings (the format is described, not
  pattern-enforced, pending a survey of non-turn record timestamps).

### Open questions

- Whether any real session projects to zero messages (all observed have talk).
- Whether `thinking` blocks should ever project (currently working-not-talk,
  like tool blocks; the session family retains them in full).
