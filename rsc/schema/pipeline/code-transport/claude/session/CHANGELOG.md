# session schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v25

The harness stops sending safeguards. Reading-room's session `e2d2039d-b1e5-4691-99f9-f0629d13e243`,
captured on 2026-10-26 by `corpus-yoga agent capture` into the stage, is refused at v24 by
the rehearsal of 2026-10-26T112156Z at its record 22488, an `api-request` whose `params`
carries no `safeguards`, which v24 required: from 2026-10-26T10:10:00Z every request record
the session writes omits the key - 53 of its 1172 - and every earlier one carries it, the
`classifier_context` v23 declared open. Read as the harness no longer passing the
safeguards parameter on its API calls; whether it returns is the next capture's to say.
No other family carries the key (rsc/model/model_join.csv names no row for it).

Validated over the staged session's conversion on reading-room, 2026-10-26: v24 refuses it
at record 22488 and stops; v25 refuses none of its 22,600 records. v25 drops one
requirement and narrows nothing, so every datum v24 admits, v25 admits.

### Replaces

v24

#### Relaxed

- `ApiRequestParams`: `safeguards` no longer required.

#### Refactored

None.

## v24

One shape of a user turn's `toolUseResult` that v23 did not admit. Reading-room's session
`e2d2039d-b1e5-4691-99f9-f0629d13e243`, captured on 2026-10-21 by `corpus-yoga agent capture`
into the stage, is refused at v23 by the rehearsal of 2026-10-21T141229Z at its record
11165: the turn that fed back the result of the VS Code diagnostics tool,
`mcp__claude-vscode__getDiagnostics`, carries `toolUseResult` as an array of one text
block - `[{"type": "text", "text": "[\n  {\n    \"uri\": ...`, the tool's result content
as the MCP server returned it - where v23 declared a string or an object. The session
holds 1722 object forms, 24 string forms and this one array; its one element is a
`TextBlock`. The held copy of the same session under data/input stops short of the turn.

Read as the harness writing an MCP tool's result content through unchanged where a built-in
tool's result is written as its own object: `ToolResultBlock.content` has carried the same
array-of-text-blocks form since v1.

Validated over the staged session's conversion on reading-room, 2026-10-21: v23 refuses it
at record 11165 and stops; v24 refuses none. v24 adds an alternative and narrows nothing,
so every datum v23 admits, v24 admits.

### Replaces

v23

#### Relaxed

- `UserTurnType.toolUseResult` - an array of `TextBlock`s beside the string and the object.

#### Refactored

- `TextBlock` - moves earlier in the file, the BFS order repair placing it where
  `UserTurnType` first references it. No validation effect.

## v23

Three record types Claude Code 2.1.300 writes that v22 did not declare. Home-room's
session `67f2899c-…`, captured on 2026-10-15 by `corpus-yoga agent capture` into the stage,
is refused at v22 by the rehearsal of 2026-10-15T110202Z at its record 835, the first
record it wrote under 2.1.300, at 2026-10-15T10:15:23Z; validation stops at the first
fault, and 187 of its 1399 records carry a type v22 does not declare. They are:
`api-request-shape`, once, the system prompt's text blocks and fifteen tool definitions
under a hash; `api-request-blob`, 157 times, one message each under a hash, the messages'
blocks of the five types text, thinking, tool_use, tool_result and `tool_addition`, the
last carrying one MCP tool's definition; and `api-request`, 29 times, one per assistant
turn, the request's parameters, its shape by hash, its messages by reference - `base`, the
previous record's id, `keep`, a count, and `tail`, blob hashes - with cache control and a
request digest. Together they are 46 percent of the file's bytes. The 21 sessions held
under data/input on home-room carry none of the three types, nor does the other session
in home-room's live store, 41ff13e9, last written 2026-09-30.

Read, from the hashes and the references, as the harness recording each API call it makes,
content-addressed - the shape once, each message once, each call as its parameters plus
what it reuses and what it adds. That is an inference: 135 of the 292 hashes the first
request's tail names have no blob in the file, and the next harness version may write
otherwise.

Two members are declared open at this mint, a decision recorded here: a tool definition's
`input_schema`, a JSON Schema document whose keys are the tool's, and a safeguard's
`classifier_context`, about 55K bytes a record nested seven deep, whose eighteen observed
top-level keys the description names. Their members are undeclared until a reading needs
them.

Validated over the staged session's conversion on home-room, 2026-10-15: v22 refuses it
at record 835 and stops; v23 refuses none. v23 adds alternatives and definitions and
narrows nothing, so every datum v22 admits, v23 admits (issues/892).

### Replaces

v22

#### Relaxed

- `Record` - three alternatives: `ApiRequestShapeRecord`, `ApiRequestBlobRecord` and
  `ApiRequestRecord`, each closed over the keys observed.
- `ApiRequestShapeRecord` - `shape`, an `ApiRequestShape` of `system`, text blocks, and
  `tools`, each a `ToolDefinition` closed over the seven keys observed across the shape's
  tools and the tool_addition blocks, `name` alone required.
- `ApiRequestBlobRecord` - `message`, an `ApiRequestMessage` whose `role` is user,
  assistant or system, whose content is a string or `ApiRequestContentBlock`s - the four
  turn block types observed plus `ToolAdditionBlock`, a `ToolAddition` carrying a
  `ToolDefinition` - with optional `output_config` and `clear_at`, each observed once.
- `ApiRequestRecord` - `params`, an `ApiRequestParams` of `model`, `betas`, `max_tokens`,
  `thinking`, `context_management` with its edits, `safeguards` with an open
  `classifier_context`, and `output_config`; `base` optional, absent on the first record;
  `keep`; `tail`, empty on one record; `cacheControl` entries of a path and a value;
  `requestDigest`.
- `HexDigest64` - a 64-character lowercase hexadecimal string, every hash and digest
  the three records carry.

#### Refactored

- `TextBlock` - moves earlier in the file, the BFS order repair placing it where
  `ApiRequestShape` first references it. No validation effect.

## v22

One key Claude Code 2.1.283 writes that v21 had closed. Home-room's session
`41ff13e9-…`, captured on 2026-10-13 by `corpus-yoga agent capture` into the stage, is
refused at v21 by the rehearsal of 2026-10-13T092955Z; validated record by record, 1 of
its 15647 records fails and no other. It is an `artifact-autoreact-ledger` record of
2026-09-27T20:16:32Z whose one entry, for the artifact `3329fd9e-…` titled "Corpus Site
Dataflow", carries `"interrupted": true` between `turnTimestamps` and `threads`, where
`ArtifactLedgerEntry` was closed over its six required keys. The ledger record before it
for the same artifact and the one 32 seconds after it carry no `interrupted`, nor do the
session's other 270 ledger records or its 31 comment-monitor records. The 21 sessions
held under data/input on home-room carry no `interrupted` and validate at v21, the held
copy of the same session, of 2026-09-17, among them.

The record is saved in the same millisecond as a queue operation carrying the user's
interrupt of a tool use, "[Request interrupted by user for tool use]", and two records
before a task notification whose summary is "1 artifact auto-reply subscription paused by
the interrupt"; the ledger record after the user's next typed message carries no
`interrupted`. The key is read, from that notification, as the watch's paused state. That
is an inference: the session's two earlier interrupts, of 2026-09-15, precede its first
comment-monitor record, and reading-room's session be12fa7c, held under data/input, has
a plain interrupt of 2026-10-07 (2.1.291) under an armed watch with no ledger record
saved and no such notification, so what makes the harness write the key is not known.

Validated over the staged session's conversion on home-room, 2026-10-13: v21 refuses
the 1 record and no other; v22 refuses none (issues/860).

### Replaces

v21

#### Relaxed

- `ArtifactLedgerEntry` - optional `interrupted`, a boolean, observed `true` on one
  entry of 2026-09-27 and absent on every other.

## v21

One key Claude Code 2.1.294 writes that v20 had closed. Reading-room's session
`e2d2039d-…`, captured on 2026-10-09 by `corpus-yoga agent capture` into the stage, is
refused at v20 by the rehearsal of 2026-10-09T131819Z; validated record by record, 3 of
its 3216 records fail and no other. Each is a user turn, a task notification, from
2026-10-09T10:57:30Z on, whose `origin` is
`{"kind": "task-notification", "producer": "session-task", "runId": "0mv0upcup-38fcf3a9"}`
where `TurnOrigin` was closed over `kind` and `producer`. The 20 sessions held under
data/input on reading-room carry no `runId` and validate at v20, as do the two other
claude sessions the rehearsal judged, 5c631cf4 and be12fa7c.

Validated over the staged session's conversion on reading-room, 2026-10-09: v20 refuses
the 3 records and no other; v21 refuses none (issues/847).

### Replaces

v20

#### Relaxed

- `TurnOrigin` - optional `runId`, a string, observed `0mv0upcup-38fcf3a9` on every
  task-notification turn from 2026-10-09.

## v20

Two shapes Claude Code 2.1.289 writes that v19 had closed. Reading-room's session
`be12fa7c-…`, captured on 2026-10-07 by `corpus-yoga agent capture --all` into the
stage, is refused at v19 by the rehearsal of 2026-10-08T194222Z; validated record by
record, 26 of its 36207 records fail and no other. Twenty-one are user turns from
2026-10-05T21:25:50Z on, each a task notification, whose `origin` is
`{"kind": "task-notification", "producer": "session-task"}` where `TurnOrigin` was
closed over `kind` alone. Five are queue-operation records from 2026-10-06T18:36:53Z
on, each a `remove` with reason `absorbed_mid_turn`, carrying `commandUuid` and
`deliveryId`, two v4 uuids, where `QueueOperation` was closed without them. The copy
of the session held under data/input, of 2026-10-04, carries neither key and
validates at v19, as do the 19 other held sessions.

The same records carry `promptSource` `system` and `turnOrigin` `task_notification`,
both admitted as strings; `promptSource`'s description now records the value. The
versions seen on the user turns carrying `producer` are 2.1.289 and 2.1.291.

Validated by hand over the staged session's conversion on reading-room, 2026-10-08:
v19 refuses the 26 records and no other; v20 refuses none (issues/827).

### Replaces

v19

#### Relaxed

- `TurnOrigin` - optional `producer`, a string, observed `session-task` on every
  task-notification turn from 2026-10-05.
- `QueueOperation` - optional `commandUuid` and `deliveryId`, each a `UuidV4`,
  observed together on every remove with reason `absorbed_mid_turn` from 2026-10-06.

#### Refactored

- `promptSource` - its description records the observed value `system`. No
  validation effect.

## v19

A member observed where v18 had seen none. v18 declared a cost-state record's
`modelUsage` an object "observed empty in every record; its members are undeclared
until observed", and closed it. Reading-room session `be12fa7c-…`, captured on
2026-09-29 by `corpus-yoga agent capture --all` into the stage, now carries five
cost-state records: the three of the v18 mint, and two more after a record of
2026-09-29T14:14:17Z whose totals are no longer 0 - `totalCostUSD` 264.73,
`totalAPIDuration` 15628591, `totalToolDuration` 3269989, 1157 lines added and 8
removed - and whose `modelUsage` holds two members keyed by model id,
`claude-fable-5-1` and `claude-haiku-4-5-20251001`, each with six integer counts
(`inputTokens`, `outputTokens`, `thinkingTokens`, `cacheReadInputTokens`,
`cacheCreationInputTokens`, `webSearchRequests`) and a `costUSD`. The rehearsal of
15:46:46Z read the log `fails claude/session v18` at the first of the two, and nothing
reached shared storage (issues/733).

`claude-haiku-4-5-20251001` was no member of `ModelId`, and authors no turn of the
session: the harness calls it beside the model that drafts. `ModelId`'s description
had said "the harness's external attribution of who authored a completed turn", which
is the definition of one member, `AssistantMessage.model`, and not of the type - the
type's five other members say of themselves that the model advised, refused, or was
fallen back to or from (the maintainer's ruling, reading-room 2026-09-30). The type is
a model id; what a model did is said where the id is carried. So `ModelId` gains the
id, and the usage is keyed by `ModelId`. The draft-04 dialect has no keyword that
types a key, so the key's type is stated in `modelUsage`'s description, as the
artifact maps' uuid keys are stated in theirs.

Validated by hand over the staged log: v18 refuses the two records and no other; v19
refuses none.

### Replaces

v18

#### Relaxed

- `CostStateRecord.modelUsage` - its members are admitted: any key, each value a
  `ModelUsage`. v18 admitted the empty object alone.
- `ModelUsage` - new: `inputTokens`, `outputTokens`, `thinkingTokens`,
  `cacheReadInputTokens`, `cacheCreationInputTokens` and `webSearchRequests` integers,
  `costUSD` a number, every one required and none observed absent; closed.
- `ModelId` - gains `claude-haiku-4-5-20251001`, in every member typed by it.

#### Refactored

- `CostStateRecord` and its totals say in their descriptions what is observed of them
  on 2026-09-29 beside the 0 of 2026-09-28.
- `ModelId`'s description defines the type, a model id as the harness names it, and
  leaves each role to the member that carries the id.
- `ModelUsage` stands after `ArtifactLedgerEntry`, where the order repair places it.

## v18

A record kind no version knew. Reading-room session `be12fa7c-…`, written by Claude
Code 2.1.283 and captured on 2026-09-28 by `corpus-yoga agent capture --all` into the
stage of pull/689's branch, carries three `cost-state` records that v17 refuses - the
session's running cost and effort totals, `totalCostUSD` and the durations and line
counts all 0, `totalDuration` climbing across the three, `modelUsage` an empty object,
`hasUnknownModelCost` false - the first written after a record of 12:57:55Z that day;
the held copy of the same session, captured before, has none, and no other captured
session of either machine has one. `corpus-yoga pipeline rehearse code-transport` read
the log `fails claude/session v17`, and nothing reached shared storage (issues/713).

The same log carries a second form, found when the mint was validated by hand: from
record 17931, of 2026-09-26T18:59:33Z, every completed assistant record - 909 of them,
every one but the log's single API-error record - carries `advisorModel`
(`"claude-fable-5-1"` throughout), `serverClassifierRequest` (a v4 uuid, 508 distinct)
and, inside `message`, `input_transformations` (an array of `{path, reason, type}`,
127 distinct paths of the form `messages.N.content.0`, reasons
`prefix_binding_mismatch` and `model_binding_mismatch`, type `thinking_dropped`
alone). The held copy of the session, captured 2026-09-17 at 17846 records, has none
of the three; the 5730 assistant records before 17931 have none.

### Replaces

v17

#### Relaxed

- `Record` - gains `CostStateRecord`: type "cost-state", `sessionId` a `UuidV4`, the six
  totals and two durations numbers, `startTime` a number, `modelUsage` an object
  observed empty and closed until a member is observed, `hasUnknownModelCost` a
  boolean; every property required, none observed absent.
- `AssistantTurnType` - optional `advisorModel` (a `ModelId`) and
  `serverClassifierRequest` (a `UuidV4`), absent on every record before 2026-09-26
  and on the API-error record.
- `AssistantMessage` - optional `input_transformations`, an array of
  `InputTransformation`: `path`, `reason` and `type`, strings, all required, the
  observed values in their descriptions.

#### Refactored

- `ModelId` stands before `RenderedBlock`, and `InputTransformation` after
  `StopDetails`: the order the BFS repair gives now that `AssistantTurnType` reaches
  `ModelId` first. No validation effect.

## v17

Two forms the artifact machinery had not yet shown. Home-room session
`41ff13e9-…`, written by Claude Code to 2.1.272 and recaptured on 2026-09-17 at
9610 records, carries 50 that v16 refuses: 49 `artifact-autoreact-ledger`
records whose entry has a `stampHighWater` of `"2026-09-15T21:24:26.450Z"`, the
non-null form v16 recorded as unobserved, arriving once a reply on the artifact
had been handled; and one `attachment` record of 2026-09-16, a `queued_command`
typed while the model worked, whose `rendered[0].content` is an array of one text
block where the session's three other queued commands render as strings.

### Replaces

v16

#### Relaxed

- `ArtifactLedgerEntry.stampHighWater`: null or a `Timestamp`, where v16 admitted
  null alone.
- `RenderedBlock.content`: a string or an array of `TextBlock`, where v16 admitted
  a string alone.

#### Refactored

- `TextBlock` and `ContentBlock` stand earlier among the definitions: the order the
  BFS repair gives now that `RenderedBlock` reaches `TextBlock` first. No validation
  effect.

## v16

The artifact machinery enters the record, and the undeclared is surveyed.
Reading-room session `be12fa7c-…`, written by Claude Code 2.1.241 to 2.1.270
and recaptured on 2026-09-15 at 16190 records, carries 513 that v15 refuses:
338 `frame-link` records carrying `artifactCount`, 336 of them a count record
with no path or url at all, from 2026-09-02; and two record types no version knew,
`artifact-comment-monitor` (30) and `artifact-autoreact-ledger` (145), the
harness's map of the artifacts a session watches for comments and its ledger
of automatic replies on them. Each is admitted below as a closed object minted
from the observed records. The same survey, over both rooms' stores, found
eighteen keys that every version admitted undeclared on the open turn records
since harness 2.1.201 (2026-07-05) - a tool denial's kind, an MCP result's
source and meta, a turn's attribution to a skill or MCP tool, an error's
text, superseded uuids, a shutdown interruption, and the nine fields of a
`model_refusal_fallback` system event; v16 declares them with the types
observed, as v15 declared the retry trio. Every session in both rooms' stores
on 2026-09-15 validates at v16: v15 now happens to reject only the kinds its
era never showed.

### Replaces

v15

#### Restricted

- user records: `toolDenialKind`, `sourceToolUseID`, `mcpMeta`,
  `interruptedByShutdown`; assistant records: `attributionSkill`,
  `attributionMcpServer`, `attributionMcpTool`, `errorDetails`,
  `supersedesUuids`; system records: `direction`, `trigger`, `scope`,
  `originalModel`, `fallbackModel`, `apiRefusalCategory`,
  `apiRefusalExplanation` (null or string), `refusedUserMessageUuid`,
  `retractedMessageUuids` - declared where v15 left them undeclared on the
  open turn records. Non-material: every held datum passes (both rooms'
  stores, 2026-09-15).

#### Relaxed

- `artifact-comment-monitor`: a new record type, `ArtifactCommentMonitorRecord`,
  a closed object of `type`, `v`, `sessionId` and `artifacts`, the last a map
  from artifact uuid to `ArtifactMonitorEntry` (`state`, `writtenAtMs`,
  `title`), all required.
- `artifact-autoreact-ledger`: a new record type,
  `ArtifactAutoreactLedgerRecord`, a closed object of `type`, `v`, `sessionId`,
  `accountUuid` and `artifacts`, the last a map from artifact uuid to
  `ArtifactLedgerEntry` (`savedAt`, `stampHighWater` observed only null,
  `everBaselined`, `everHadThreads`, `turnTimestamps` and `threads` observed
  only empty), all required.
- `frame-link`: a second shape under the one type - the count record, `type`,
  `sessionId`, `timestamp` and `artifactCount` alone (336 of reading-room's
  records, from 2026-09-02) beside the publish record; `path` and `frameUrl`
  are no longer required, and a dependency keeps them a pair; `artifactCount`,
  an integer, may also ride a publish record (2 observed).

#### Refactored

- `MessageContent` moves in the file: the breadth-first order repair places it
  after the definitions the new record types reference. No validation effect.

## v15

The harness's growth over a month enters the record. Home-room session
`41ff13e9-…`, written by Claude Code 2.1.263 to 2.1.270 between 2026-09-07
and 2026-09-15 (entrypoint claude-vscode, through the VS Code bridge) and
captured on 2026-09-15 by `corpus-yoga agent capture --provider claude`,
carries 1598 records of 5101 that v14 refuses. Its first record is of a type
no version knows, `bridge-session`, so no version admits the session at all.
Validating the session record by record against v14: the bridge session
records (237) fail as an unknown type; the assistant records (1358) fail on
`effort`, `apiBlockIndex`, and from 2.1.269 `perTurnEffort`,
`wireToolInputs` and `wireIngestContext`; the three `remove` queue
operations fail on `reason`; user records carry `origin`, `promptSource`,
`classifierMetaLines` and `queueSkipAttachments`, attachment records
`rendered` and `renderedInHumanTurn` - each admitted below with the type
observed - and every assistant record names a model the id set had not seen,
claude-fable-5-1. The api_error system records also carry `retryInMs`,
`retryAttempt` and `maxRetries`; those are not new - reading-room's sessions
carry them from harness 2.1.156 - and v14 admitted them undeclared on the
open system record; v15 declares them. Every other session in both rooms'
stores on 2026-09-15 validates at v14 and validates at v15 unchanged: v14 now
happens to reject only the kinds its era never showed.

### Replaces

v14

#### Restricted

- system records: `retryInMs` (number, 0 upward - fractional values observed),
  `retryAttempt` and `maxRetries` (integers, 0 upward), declared where v14 left
  them undeclared on the open system record. Non-material: every held datum
  passes (60 api_error records across both rooms' stores, 2026-09-15).

#### Relaxed

- `message.model`: the model id set gains claude-fable-5-1 (home-room,
  harness 2.1.263, first observed 2026-09-07), the fifth real model.
- `bridge-session`: a new record type, `BridgeSessionRecord`, a closed object
  of `type`, `sessionId`, `bridgeSessionId`, `lastSequenceNum`,
  `ownerAccountUuid` and `ownerOrganizationUuid`, all six required since all
  are present on every observed record.
- assistant records: `effort` and `perTurnEffort` (strings, "high" observed),
  `apiBlockIndex` (integer, 0 to 5 observed), `wireToolInputs`
  (`WireToolInputs`: an object keyed by tool_use id, each an object) and
  `wireIngestContext` (`WireIngestContext`: an object keyed by tool_use id,
  each an object with `cwd`).
- user records: `origin` (`TurnOrigin`: a closed object with `kind`, "human"
  and "task-notification" observed), `promptSource` (string, "sdk"),
  `classifierMetaLines` (string), `queueSkipAttachments` (boolean).
- attachment records: `rendered` and `renderedInHumanTurn`, arrays of
  `RenderedBlock` (a closed object with `content`).
- queue operations: `reason` (string, "absorbed_mid_turn" on remove).

#### Refactored

None.

## v14

The harness's refusal enters the record. Reading-room session `5c631cf4-…`,
resumed on 2026-08-22 (harness 2.1.240, entrypoint claude-vscode), carries one
assistant record written at 22:37:35Z that no version admits: an API-error
message (`isApiErrorMessage` true, `error` invalid_request) whose
`message.model` is the not-a-model marker, whose `stop_reason` is "refusal" -
the free string every version admits - and whose `stop_details`, null on every
record of every session until that evening, is an object: type "refusal",
category "reasoning_extraction", the harness's explanation sentence,
`fallback_has_prefill_claim` false, `recommended_model` null. The 2026-08-23
survey over both rooms' stores and this checkout's cache found a non-null
`stop_details` in this one record only; validating the session record by
record against v13, it is the only failure. Every record valid under v13 is
valid under v14 unchanged: v13 now happens to reject only the kind its era
never showed.

### Replaces

v13

#### Restricted

None.

#### Relaxed

- `message.stop_details`: null-only becomes null-or-`StopDetails`, a closed
  five-field object (`type`, `category`, `explanation`,
  `fallback_has_prefill_claim`, `recommended_model`) - all five present in the
  observed record, so all required; `recommended_model` null-or-string, the
  one field observed only null.

#### Refactored

- The four content-block descriptions that cite the MCP counterpart (TextContent,
  ToolUseContent, ToolResultContent, ImageContent) name it as
  `rsc/reference/mcp#/$defs/…` (issues/572); they had named a snapshot file path that
  pull/558 deleted. No validation effect.
- `MessageContent` spells its union as `type: ["string", "array"]` with
  `minItems` and `items` beside - keywords draft-04 applies to the array member
  alone - instead of a `oneOf` of two inline types (2026-09-08, reading-room,
  judged against the documenter `rsc/rpus/documenter.json`). No validation
  effect.

---

## v13

The session log grows a lifecycle record kind. Reading-room session
`5c631cf4-…` (2026-08-17 to 2026-08-22, harness 2.1.234 to 2.1.240,
entrypoint claude-vscode) carries 70 records of a type no version names:
`{"type": "atis-latch", "atis": "", "sessionId": …}` - the ModeRecord family
(type, one string, sessionId; no timestamp), first written 2026-08-19T09:53Z
under 2.1.234. The 2026-08-22 survey over both rooms' stores and the live
projects found them in this one session only, `atis` the empty string in every
one, no further key; validating the session record by record against v12,
these 70 are the only failures. What the harness means by atis the corpus
does not say. Every record valid under v12 is valid under v13 unchanged: v12
now happens to reject only the kind its era never showed.

### Replaces

v12

#### Restricted

None.

#### Relaxed

- `Record` - gains `AtisLatchRecord`: type "atis-latch", `atis` a string
  (observed only as the empty string; the set is open), `sessionId` the
  session uuid; closed to other keys, so the next key the harness adds fails
  loudly by name (first observed 2026-08-19T09:53Z, reading-room, harness
  2.1.234).

#### Refactored

None.

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

v11

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

v10

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

v9

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

v8

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

v7

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

v6

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

v5

#### Relaxed

- `FrameLinkRecord` — new `Record` variant, discriminator `type: "frame-link"`: links the
  session to a web Artifact it published (`sessionId`, `path`, `frameUrl`, `timestamp` —
  all five fields present in both observed records, so all required; closed). `path` is an
  absolute machine-local path and `frameUrl` is stable across redeploys — one record per
  publish, same URL.

## v5

Now validates `3b98fa60-…` (2026-07-05, the session that raised this repo's pull/1–pull/3 from
the second machine) — the first session in which Claude Code created pull requests, and so
the first to carry the record type this version admits. Aptly, the very session that
exposed the gap is the evidence for closing it; more aptly still, the prediction that the
PR proposing this version would write `pr-link` records into the session raising it CAME
TRUE and was verified: moments after `gh pr create` raised pull/4, the raising session
(`a6f25723-…`) gained `{"type": "pr-link", "prNumber": 4, …}` and on revalidation reads
"modelled by v5; not by v1, v2, v3, v4" — the second datum of the record type, produced by
the act of proposing it, validating only against the version it carries in its own diff.
(Provenance, learned the same way: the record is written by the harness asynchronously
when a PR is created from a session's shell — a first check that ran too early reported a
false negative.)

### Replaces

v4

#### Relaxed

- `PrLinkRecord` — new `Record` variant, discriminator `type: "pr-link"`: links the session
  to a GitHub pull request it created or updated (`prNumber`, `prUrl`, `prRepository`,
  `sessionId`, `timestamp` — all six fields present in all 59 observed records, so all
  required). Heartbeat-style like `ai-title`: re-emitted with fresh timestamps while the
  PR context is active (59 records across 3 PRs in the one observed session).

## v4

### Replaces

v3

#### Relaxed

- `ModeRecord` — new record type (`type: "mode"`) with required `mode: string` and `sessionId: UuidV4`. Observed with `mode: "normal"`. Written alongside other session lifecycle records. Sessions `83737fec` and `57289774` now pass; they fail v1–v3. Sessions `89515719` and `df71fdce` originally passed v1–v3 (registered before they emitted a `mode` record); both have since grown to include one, so they now fail v1–v3 and pass only v4 — the same transition, observed live.

---

## v3

### Replaces

v2

### Relaxed

- Added `DocumentBlock` content block type (`type: "document"`) to `ContentBlock.oneOf`. Observed when Claude Code passes a file as context to the model. Block shape: `{type, source: {type, media_type, data}, title}`. All observed instances have `source.type: "text"` and `source.media_type: "text/plain"`. Session `32bd7448` now passes; it fails v1 and v2.

### Refactored (description only)

- `AiTitleRecord.description`: corrected "Written once early in the session" to reflect observed behaviour — written repeatedly throughout the session (~299 times in a 4868-record session), appearing to be a heartbeat rather than a one-time write. No validation change.
- `AiTitleRecord.description`: further updated to reflect that the title is also set by user rename via the VS Code UI — all sources write the same record type with no distinguishing field; last record wins (`currentSessionTitle`).
- `AiTitleRecord.properties.aiTitle.description`: clarified that despite the field name the value is not exclusively AI-generated; also set by user rename. Last-wins semantics.

---

## v2

### Replaces

v1

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
discovered iteratively by running `src/main/pipeline/code-transport/run.sh` and re-tightening:

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
