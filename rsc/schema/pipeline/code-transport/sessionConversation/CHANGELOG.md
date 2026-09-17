# sessionConversation schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v2

Minted 2026-09-17 on home-room so that a gemini code session projects into this family
beside claude's (#635). Validates the projections of the two captured Antigravity
sessions, home-room's 5bb62af7 (2 turns) and reading-room's a821b300 (227 turns), and every claude
session as before.

### Replaces

v1

#### Restricted

- `SessionConversation` requires `provider`, the provider whose harness recorded the
  session, and `harness`, that harness's name: a conversation says whose it is, and the
  render reads both from it and from nowhere else. Every projection is rewritten by its
  provider's `project_conversation.py` on the run that brings this version.

#### Relaxed

- `Message.uuid` is optional. A claude record carries a uuid; an Antigravity step carries
  none, its step indices repeating where the harness resumed the session, so a gemini
  turn is anchored in the corpus by role and count, as a gemini chat's turns are.

#### Refactored

- The family description names no one provider: what projects is each provider's own rule,
  stated in its `project_conversation.py`; claude's follows as before. The corpus root reads
  `data/output/markdown/<provider>/code/conversations/`. No validation effect.
- `title`, `session_id`, `created`, `last_activity` and `Message.timestamp` say what each
  is for either provider: the title's source, the name the harness stores the session
  under, and timestamps to the harness's own precision (claude milliseconds, gemini
  seconds). No validation effect.

## v1

Inaugural version, minted 2026-07-11 from the six local sessions (two projects).
The family models a session read as TALK: `project_conversation.py` projects each
converted session (`session.json`, the `session` family's datum) to a
`conversation.json` beside it — user and assistant records only (no sidechains,
no meta records, no tool-result carriers), each reduced to its visible text; a
record whose projection is empty contributes no turn. Roles use the corpus
vocabulary (`human`/`assistant`, matching `browser-captures/markdownConversation`)
because this shape is the projection source for the session corpus render under
`output/markdown/claude/code/conversations/`.

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

#### Refactored

- `SessionConversation` and `.uuid` descriptions (v1, in place) — the render path re-rooted
  `output/markdown/claude/code/conversations/` → `data/output/…`, and the cache reference
  `cache/` → `tmp/cache/`, for the four-root migration (#20), which `rsc/schema/` was
  excluded from sweeping. No validation effect.
