# projectMemory schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v2

The memory system began stamping update times. A fact edited after that
carries a fourth metadata key — `modified`, ISO-8601 UTC with milliseconds
— first observed in home-room's store 2026-07-18 and reading-room's
2026-07-19; the 2026-07-22 survey found 3 of 25 facts across both rooms'
stores carrying it, putting both rooms' repo-project memories outside v1
(first noticed 2026-07-21, in the four-root migration's dry-run worktree).
Every datum valid under v1 is valid under v2 unchanged: v1 now happens to
reject only the key its era never showed.

### Replaces

[v1.json](./v1.json)

#### Restricted

None.

#### Relaxed

- `Metadata.modified` — new optional key: the fact's last-update time,
  harness-stamped when a session edits an existing fact; absent on facts
  never edited since the stamping began (22 of 25 observed).

#### Refactored

None.

## v1

Inaugural version, minted 2026-07-11 from the two local projects carrying a
`memory/` directory. The family models a project's whole memory state as one
datum: `memory_to_json.py` parses `input/claude/code/machine-transport/<room>/<project>/memory/` —
the `MEMORY.md` index plus one frontmattered markdown file per fact — into
`cache/code-agents/<room>/<project>/memory/memory.json`. Facts carry identity
(`name`), classification (`metadata`), body, and extracted `[[link]]` targets;
index lines that are not entries (headings, `agent.py`'s merge marker
comments, prose) are carried verbatim as `unparsed`.

Evidence notes:

- `facts` — may be empty: one observed project's memory is a guard-only
  `MEMORY.md` with no fact files (all its index lines land in `unparsed`).
- `Metadata` — every observed fact carries all three keys (`node_type`,
  `type`, `originSessionId`), so all three are required; the harness stamps
  `node_type` and `originSessionId` when a session writes a fact.
- `Metadata.node_type` — `memory` is the only observed value; closed enum,
  so a new node type fails loudly.
- `Metadata.type` — closed enum over the memory format's four prescribed
  classes (`user`, `feedback`, `project`, `reference`); observed locally:
  `feedback`, `reference`, `project`. Non-material for `user`: prescribed
  but not yet observed here.

### Open questions

- Whether a hand-authored fact (no harness stamping) can lack
  `originSessionId` — would relax `Metadata.required` in a v2.
- Whether re-dressed twins (`<stem>.<room>.md`, minted by `receive` on
  divergence) appear in local data; the shape models them (name/file split)
  but none is yet observed.
