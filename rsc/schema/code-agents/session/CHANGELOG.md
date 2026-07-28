# session schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v12

The model enum meets the model family it was built to catch. Reading-room
session `dabe819e-…` (2026-07-25, harness 2.1.220, entrypoint claude-vscode)
carried assistant turns authored by `claude-opus-5` — and v9's closed
`ModelId` did exactly what it was minted for: the new model failed validation
by name instead of sliding through a string. The 2026-07-28 survey found
3,588 such records, all in reading-room's store; home-room shows none. Every
datum valid under v11 is valid under v12 unchanged: v11 now happens to
reject only the id its era never showed.

Recorded from the same survey, observed but not modelled: the era's records
carry turn-level keys the open turn object admits without a version boundary
— `effort` (8,134 records across both rooms, value `high` only),
`attributionSkill` (138), `attributionMcpTool`/`attributionMcpServer` (31
each), `errorDetails` (2). They pass every version silently, so no mint
marks their arrival; closing the turn object would give fields the same
drift-fails-loudly property `ModelId` gives models, and that judgment is
left open here.

### Replaces

[v11.json](./v11.json)

#### Restricted

None.

#### Relaxed

- `ModelId` — gains `claude-opus-5` (reading-room's sessions, first observed
  2026-07-25T10:29Z). `FallbackBlock.from.model` / `.to.model` widen with it,
  as they reference `ModelId`; no opus-5 fallback is yet observed.

#### Refactored

None.

## v11

The file-history ledger reaches outside the repo. Reading-room session
`5d680541-…` (2026-07-21, the memory work) edited a memory fact under
`~/.claude/projects/<project>/memory/` — a file OUTSIDE the session cwd —
and the resulting `file-history-delta` is the store's first whose
`trackingPath` is absolute and whose `backup` carries a fourth key:
`realParentDir`, the tracked file's real parent directory (`backupFileName`
null in the same record — no prior content to back up). The 2026-07-22
survey found 73 deltas across both rooms' stores; this record alone carries
the key. Every record valid under v10 is valid under v11 unchanged: v10 now
happens to reject only the shape its era never showed.

### Replaces

[v10.json](./v10.json)

#### Restricted

None.

#### Relaxed

- `FileHistoryBackup.realParentDir` — new optional key: absolute directory
  of the tracked file when it lives outside the session cwd; absent on
  ordinary in-repo edits (72 of 73 observed deltas).

#### Refactored

- `FileHistoryDelta.trackingPath` — description now records the absolute
  form the out-of-cwd record showed; the type was already `string`, so no
  validation change.

## v10

The file-history ledger grows a second grain. Reading-room session `eeafe24c-…`
(2026-07-13 → 14, the yoga-serve and xref-gitignore work) crossed three harness
builds overnight — 2.1.207 through 2.1.209 — and 23 minutes into the 2.1.208 era
the log's first `file-history-delta` appeared: where `file-history-snapshot`
records a turn's whole tracked-backup map, the delta records ONE file's backup
at edit time. Ten records observed, all in that session; 4 of its 47 snapshots
carry linked deltas. Every record valid under v9 is valid under v10 unchanged:
the mint admits its triggering records and nothing else — v9 now happens to
reject only the record type its era never showed.

### Replaces

[v9.json](./v9.json)

#### Relaxed

- `FileHistoryDelta` — new `Record` variant, discriminator `type:
  "file-history-delta"`: one tracked file's backup at edit time —
  `messageId` (the editing turn), `snapshotMessageId` (resolves to a
  `file-history-snapshot` in the same log, 10 of 10 observed), `trackingPath`
  (cwd-relative path of the edited file), `backup`, `timestamp`. All six
  fields present in every observed record, so all required; closed.
- `FileHistoryBackup` — the delta's `backup`: `backupFileName` names the
  stored copy in `~/.claude/file-history/` (`<16 hex>@v<version>`, the suffix
  agreeing with the `version` field in every observed record) and is nullable —
  null once, for a file created new in the session, no prior content to back
  up; `version` (ordinal, only 1 observed); `backupTime`. All three fields
  present in every observed record, so all required; closed.

## v9

The model field earns a type system. Since v1 `AssistantMessage.model` was a bare
string, which let one value hide in plain sight: `"<synthetic>"` is not a model id
but the harness's marker for records NO model authored (semantically null —
limit-death tombstones and other deterministic records rendered as agent speech;
the forensics of 2026-07-10, surfaced when `yoga agent models` censused both
rooms). v9 splits the field into two named types so the distinction is structural,
not tribal: `ModelId` (the real ids, exhaustive over both rooms' observed data)
and `NotAModel` (the lone `"<synthetic>"`). A new model in the data now fails
validation by name — model drift mints a version instead of sliding through a
string.

### Replaces

[v8.json](./v8.json)

#### Restricted (non-material)

The restriction excludes no observed record: every datum that passed v8 passes
v9 — both home-room sessions rest at v9 unchanged, and reading-room's census
(2026-07-10) shows only in-enum values, so its logs are expected to follow. The
tightening bites only futures: a new model id, or a marker where a model
belongs, now fails by name instead of sliding through a string.

- `AssistantMessage.model` — was any string; now `oneOf` [`ModelId`, `NotAModel`].
  `ModelId` enumerates the observed ids: `claude-fable-5`, `claude-opus-4-8`
  (home-room's sessions), `claude-sonnet-4-6` (reading-room's census,
  2026-07-10). `NotAModel` holds only `"<synthetic>"`.
- `FallbackBlock.from.model` / `.to.model` — now `ModelId`: a fallback moves
  between real models, never to the synthetic marker (observed pairs confirm:
  only `claude-fable-5` → `claude-opus-4-8`).

#### Refactored

- MCP cross-references in the TextBlock / ToolUseBlock / ToolResultBlock /
  ImageBlock descriptions (in v1–v9, in place, no validation effect) —
  `../../_reference/mcp.json#…` → `../../_reference/mcp/v1.json#…` when the protocol
  snapshot joined the versioned-family system (2026-07-10). Pinned to v1
  deliberately: these descriptions correspond to the snapshot as it stood when
  they were written.

## v8

The frontier datum is again `a6f25723-…`, and again it outgrew the schema by doing —
this time a thing it had already done once. On 2026-07-09 it published a second web
Artifact ("Schematise the surface — the Gemini arc"), and the harness's `frame-link`
record arrived one field richer than the two v6-era records that minted the type: it
now carries the page's display `title`. One record observed with it, two before it
without — so the field is optional and v8 is a pure relaxation, modelling both
vintages. A session schema minted from inside the session it validates, for the third
version running: v6 read this session's first publishes, v7 its forced fallback, v8
the record of the artifact that documented v7's arc.

### Replaces

[v7.json](./v7.json)

#### Relaxed

- `FrameLinkRecord` — optional `title` (string): the published artifact's display
  title. Observed 2026-07-09 in the one record written since; the two 2026-07-07
  records predate the field and rest unchanged (the record stays otherwise closed:
  `additionalProperties: false`, five original fields required).

## v7

Adds `FallbackBlock`, the record of an involuntary model fallback within a single
assistant turn. Surfaced first by the reading-room fork of `a6f25723-…` (which fell to
Opus on 2026-07-07), and exhibited by the very session that minted this version — the
local frontier datum forcing v7. The mechanical trace, read from that session's own log:
the message `model` field reads `claude-fable-5` through 2026-07-08T13:36; at 13:37, a
`system` record of subtype `model_refusal_fallback` (`apiRefusalCategory: "cyber"`,
raised on the agent's own output during reverse-engineering of a local binary and sqlite
store — not on any user input), an assistant turn carrying a `fallback` content block,
and the `model` field reading `claude-opus-4-8` for the 81 turns that followed.
`usage.iterations` shows the seam is intra-turn: one response begun under `claude-fable-5`
(406 output tokens) and finished under `claude-opus-4-8` (961) — two models, one turn,
one uuid.

The harness records only the involuntary direction. A fallback TO a model leaves this
block; a voluntary return leaves none, inferable at most from the `model` field changing
on later turns — so the log is a complete account of forced switches and a silent one
about reversions.

Worth recording as method, since the schema was written inside the affected session: the
`model` field is the harness's external attribution of each completed turn, and it is the
only authority available — a running agent has no introspective access to its own model.
In this datum a documented switch produced no corresponding change in the agent's
self-report, which went on naming the prior model for dozens of turns; the block marks
from the outside what the inside cannot perceive. This narrative therefore claims nothing
about who authored any turn beyond the harness's own attribution. (The same event family
also emits the `api_error` system subtype and a `fallback_message` iteration inside
`usage`; both already validate — `SystemRecordType` and `usage` are open — so only the
assistant-turn content block needed modelling.)

### Replaces

[v6.json](./v6.json)

#### Relaxed

- `FallbackBlock` — new `ContentBlock` variant, discriminator `type: "fallback"`: an
  automatic model fallback recorded inline in the assistant turn (`from`/`to`, each an
  object with a `model` string). Emitted only for the involuntary harness fallback TO a
  model (observed `claude-fable-5` → `claude-opus-4-8`); a user's voluntary switch BACK
  leaves no block, visible only as the message `model` changing — the schema records
  when the harness overrides the user, not when the user reclaims control. `from`/`to`
  are left open (not `additionalProperties: false`): only `model` has been observed, but
  a fallback envelope may well carry more.

## v6

Now validates `a6f25723-…` (2026-07-04 →, the session of the yoga CLI, the plans, the
transports, and the reformed run log — reading which surfaced this very failure as its
first catch). The session published the rpus.co/yoga landing page as a web Artifact,
twice; the harness wrote a `frame-link` record per publish, and the session outgrew v5
by the same motion v5 itself was minted for: doing a new kind of durable thing. One
record type per kind of thing a session publishes — a PR at v5, a page at v6.

### Replaces

[v5.json](./v5.json)

#### Relaxed

- `FrameLinkRecord` — new `Record` variant, discriminator `type: "frame-link"`: links the
  session to a web Artifact it published (`sessionId`, `path`, `frameUrl`, `timestamp` —
  all five fields present in both observed records, so all required; closed). `path` is an
  absolute machine-local path and `frameUrl` is stable across redeploys — one record per
  publish, same URL.

## v5

Now validates `3b98fa60-…` (2026-07-05, the session that raised this repo's PRs #1–#3 from
the second machine) — the first session in which Claude Code created pull requests, and so
the first to carry the record type this version admits. Aptly, the very session that
exposed the gap is the evidence for closing it; more aptly still, the prediction that the
PR proposing this version would write `pr-link` records into the session raising it CAME
TRUE and was verified: moments after `gh pr create` raised PR #4, the raising session
(`a6f25723-…`) gained `{"type": "pr-link", "prNumber": 4, …}` and on revalidation reads
"modelled by v5; not by v1, v2, v3, v4" — the second datum of the record type, produced by
the act of proposing it, validating only against the version it carries in its own diff.
(Provenance, learned the same way: the record is written by the harness asynchronously
when a PR is created from a session's shell — a first check that ran too early reported a
false negative.)

### Replaces

[v4.json](./v4.json)

#### Relaxed

- `PrLinkRecord` — new `Record` variant, discriminator `type: "pr-link"`: links the session
  to a GitHub pull request it created or updated (`prNumber`, `prUrl`, `prRepository`,
  `sessionId`, `timestamp` — all six fields present in all 59 observed records, so all
  required). Heartbeat-style like `ai-title`: re-emitted with fresh timestamps while the
  PR context is active (59 records across 3 PRs in the one observed session).

## v4

### Replaces

[v3.json](./v3.json)

#### Relaxed

- `ModeRecord` — new record type (`type: "mode"`) with required `mode: string` and `sessionId: UuidV4`. Observed with `mode: "normal"`. Written alongside other session lifecycle records. Sessions `83737fec` and `57289774` now pass; they fail v1–v3. Sessions `89515719` and `df71fdce` originally passed v1–v3 (registered before they emitted a `mode` record); both have since grown to include one, so they now fail v1–v3 and pass only v4 — the same transition, observed live.

---

## v3

### Replaces

[v2.json](./v2.json)

### Relaxed

- Added `DocumentBlock` content block type (`type: "document"`) to `ContentBlock.oneOf`. Observed when Claude Code passes a file as context to the model. Block shape: `{type, source: {type, media_type, data}, title}`. All observed instances have `source.type: "text"` and `source.media_type: "text/plain"`. Session `32bd7448` now passes; it fails v1 and v2.

### Refactored (description only)

- `AiTitleRecord.description`: corrected "Written once early in the session" to reflect observed behaviour — written repeatedly throughout the session (~299 times in a 4868-record session), appearing to be a heartbeat rather than a one-time write. No validation change.
- `AiTitleRecord.description`: further updated to reflect that the title is also set by user rename via the VS Code UI — all sources write the same record type with no distinguishing field; last record wins (`currentSessionTitle`).
- `AiTitleRecord.properties.aiTitle.description`: clarified that despite the field name the value is not exclusively AI-generated; also set by user rename. Last-wins semantics.

---

## v2

### Replaces

[v1.json](./v1.json)

### Refactored

- Extracted the root array type into a `Session` definition (`"type": "array", "minItems": 1, "items": {"$ref": "#/definitions/Record"}`), making the root consistent with every other top-level type in the schema (which use the `allOf` + `$ref` wrapper pattern). No change to validation behaviour — all sessions that pass v1 pass v2 and vice versa.

---

## v1

Initial schema. Validated against two Claude Code sessions from the
`claude-export-yoga` project.

### Record types

| Type | `additionalProperties` | Notes |
| --- | --- | --- |
| `user` | open (composition) | |
| `assistant` | open (composition) | |
| `attachment` | open (composition) | |
| `system` | open (composition) | |
| `queue-operation` | closed | |
| `permission-mode` | closed | |
| `last-prompt` | closed | `leafUuid` optional — absent in some observed records |
| `file-history-snapshot` | closed | |
| `ai-title` | closed | |

Turn-like records (`user`, `assistant`, `attachment`, `system`) share a `TurnBase`
envelope via `allOf`. `TurnBase` is intentionally open (`additionalProperties` absent)
because in draft-4, `additionalProperties` on a base schema used in `allOf` does not
see properties defined in sibling schemas — closing it would incorrectly reject the
type-specific fields added by each subtype.

### Content block types

| Type | `additionalProperties` | MCP counterpart |
| --- | --- | --- |
| `text` | closed | `TextContent` |
| `tool_use` | closed | `ToolUseContent` (adds `caller`) |
| `tool_result` | closed | `ToolResultContent` (snake_cased fields) |
| `thinking` | closed | — |
| `image` | closed | `ImageContent` (different structure) |

### AssistantMessage fields discovered during validation

`AssistantMessage` has `additionalProperties: false`. The following fields were
discovered iteratively by running `src/main/code-agents/run.sh` and re-tightening:

| Field | Type | Notes |
| --- | --- | --- |
| `stop_sequence` | `["null", "string"]` | Empty string observed on rate-limit responses |
| `diagnostics` | `["null", "object"]` | Cache miss reason and similar metadata |
| `context_management` | `["null", "object"]` | `{applied_edits: [...]}` when context was managed |
| `container` | `"null"` | Always null in observed exports |

### Multi-type fields

Fields that are genuinely polymorphic across observed records, typed with `type` arrays:

| Field | Type | Observed values |
| --- | --- | --- |
| `UserTurnType.toolUseResult` | `["string", "object"]` | Rejection message string; object form not yet sampled |
| `AssistantTurnType.error` | `["string", "object"]` | `"rate_limit"` string; object form not yet sampled |
| `AttachmentRecordType.attachment` | `["string", "object"]` | JSON object (`deferred_tools_delta`); Python repr string in older exports |
| `SystemRecordType.content` | `["null", "string"]` | Null for `turn_duration`; `"Conversation compacted"` for `compact_boundary` |
| `ToolResultBlock.content` | `["string", "array"]` | Plain string (common); array of text blocks for richer results |
| `AssistantMessage.stop_reason` | `["null", "string"]` | Null mid-stream; `"tool_use"`, `"stop_sequence"` etc. when complete |
| `AssistantMessage.stop_sequence` | `["null", "string"]` | Null or empty string |
| `AssistantMessage.context_management` | `["null", "object"]` | See above |
| `AssistantMessage.diagnostics` | `["null", "object"]` | See above |

### Open questions

- `AttachmentRecordType.attachment` — Python repr string form not yet confirmed in current
  exports; only JSON object form observed. The repr form may be from older Claude Code versions.
- `FileHistorySnapshotPayload.trackedFileBackups` — internal structure not yet surveyed.
- `Entrypoint` enum — `cli` and `claude-vscode` observed; treated as closed pending further exports.
- `TurnBase.userType` — only `"external"` observed; presumably `"internal"` exists.
- `UserTurnType.toolUseResult` object form — string form observed; object form documented but not sampled.
- `AssistantTurnType.error` object form — string form observed; object form documented but not sampled.
