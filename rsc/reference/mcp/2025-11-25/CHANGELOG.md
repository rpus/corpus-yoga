# mcp 2025-11-25 changelog

The 2025-11-25 lineage of the Model Context Protocol schema, held verbatim under `rsc/reference/mcp/2025-11-25/` at the upstream commit its `provenance.csv` rows pin (#587): one section per pin, newest first; the first section states the change from the lineage before it. A definition named here is the type of that name exported by `schema.ts` (`../generate.md` states the correspondence and the generation).

---

## c4c367f9f58296a7053f5c78a52fd02bfbb56a49

Taken 2026-09-09 (reading-room) by `corpus-yoga reference sync`'s procedure from upstream's `schema/2025-11-25/` at commit `c4c367f9f58296a7053f5c78a52fd02bfbb56a49`, the newest commit touching that directory on upstream's main (upstream's fix of 2026-07-27, "schema: fix 2025-11-25 NumberSchema min/max/default to number in generated JSON": `NumberSchema.minimum`, `.maximum` and `.default` retyped from `integer` to `number` - three lines, nothing else, a fractional bound or default admitted as the protocol always intended). 145 definitions under `$defs`, `$schema` `https://json-schema.org/draft/2020-12/schema`; schema.json 174,323 bytes, SHA256 `268a5f82ba70fd7e4b6dc4aa1e64f116f74b4d0edcb69dc046829c79dd4e97e7`; schema.ts 66,671 bytes, SHA256 `e74b56e73b2e37bdb595f74ba22e428ad7f07aa3519355ba661d681298ed38ac`.

The house held this lineage before #572 as the schema family `rsc/schema/_reference/mcp` (v1 at 357adac, v2 at this commit), converted to draft-04 (`$defs` to `definitions`, refs rewritten, draft-04 `$schema`); the conversion had been dialect-partial all along - 93 `const` keywords survived verbatim under a description claiming draft-04, each vacuous to a draft-04 validator - and retired with #561, which took 2026-07-28 verbatim. `rsc/model/model_join.csv`'s `mcp_path` pointers were judged against this lineage (#589 re-judges them against 2026-07-28).

The protocol at this lineage, the last with two directions: `ClientRequest` a union of 17, `ServerRequest` of 8 (`ping`, `sampling/createMessage`, `roots/list`, `elicitation/create` and the four task requests), `ClientNotification` of 5, `ServerNotification` of 9, `ClientResult` of 8, `ServerResult` of 14; opened by `initialize`; `ping` and `logging/setLevel` are methods, and Tasks is a layer of its own (`tasks/get`, `tasks/list`, `tasks/result`, `tasks/cancel`, `CreateTaskResult`, `TaskAugmentedRequestParams`), the asynchronous form of a long request. Tagged on 120 of 153 declarations, the house layer rule partitions the 145 definitions as session 37, agentic 31, jsonrpc 19, tasks 14, resources 14, prompts 13, content 9, tools 8; against 2025-06-18 the agentic layer doubles (15 to 31: sampling's tool use and tool result content, the elicitation forms and URL mode, the params objects split out of every request), tasks arrives (0 to 14), session grows (25 to 37) and the rest by a few. The wire's dialect moves to 2020-12 (`$defs`).

### Replaces

2025-06-18

#### Restricted

- Definition names absent (1): `JSONRPCError`.

#### Relaxed

- Tasks - `tasks/get`, `tasks/list`, `tasks/result`, `tasks/cancel`, `CreateTaskResult`, `TaskAugmentedRequestParams`: a long request may run as a task the client polls, and a server may ask the client to run one; `ServerRequest` grows from 4 to 8 and `ClientResult` with it.
- Sampling carries tool use and tool result content (`ToolUseContent`, `ToolResultContent`, `ToolChoice`) - the model-facing message shape the corpus families share (`rsc/model/model_join.csv`).
- Elicitation gains a URL mode (`ElicitRequestURLParams`) beside the form, and `notifications/elicitation/complete`.
- Methods new: `notifications/elicitation/complete`, `notifications/tasks/status`, `tasks/cancel`, `tasks/get`, `tasks/list`, `tasks/result`.
- Definition names new (55): `CallToolRequestParams`, `CancelTaskRequest`, `CancelTaskResult`, `CancelledNotificationParams`, `CompleteRequestParams`, `CreateMessageRequestParams`, `CreateTaskResult`, `ElicitRequestFormParams`, `ElicitRequestParams`, `ElicitRequestURLParams`, `ElicitationCompleteNotification`, `Error`, `GetPromptRequestParams`, `GetTaskPayloadRequest`, `GetTaskPayloadResult`, `GetTaskRequest`, `GetTaskResult`, `Icon`, `Icons`, `InitializeRequestParams`, `JSONRPCErrorResponse`, `JSONRPCResultResponse`, `LegacyTitledEnumSchema`, `ListTasksRequest`, `ListTasksResult`, `LoggingMessageNotificationParams`, `MultiSelectEnumSchema`, `NotificationParams`, `PaginatedRequestParams`, `ProgressNotificationParams`, `ReadResourceRequestParams`, `RelatedTaskMetadata`, `RequestParams`, `ResourceRequestParams`, `ResourceUpdatedNotificationParams`, `SamplingMessageContentBlock`, `SetLevelRequestParams`, `SingleSelectEnumSchema`, `SubscribeRequestParams`, `Task`, `TaskAugmentedRequestParams`, `TaskMetadata`, `TaskStatus`, `TaskStatusNotification`, `TaskStatusNotificationParams`, `TitledMultiSelectEnumSchema`, `TitledSingleSelectEnumSchema`, `ToolChoice`, `ToolExecution`, `ToolResultContent`, `ToolUseContent`, `URLElicitationRequiredError`, `UnsubscribeRequestParams`, `UntitledMultiSelectEnumSchema`, `UntitledSingleSelectEnumSchema`.

#### Refactored

- The generated dialect moves from draft-07 `definitions` to 2020-12 `$defs`.
- Every request's parameters become a named object (`CallToolRequestParams`, `CreateMessageRequestParams`, `ReadResourceRequestParams`, ...) where the lineage before inlined them.
- `JSONRPCError` becomes `Error`, the JSON-RPC error object named as itself.

## 357adac

The lineage as first taken, 2026-07-10 (reading-room), at upstream commit 357adac and converted to draft-04. Lived as a single flat file beside the family (no versions, no changelog, updated in place) until 2026-07-10, when the reference joined the versioned-family system as `_reference/mcp/v1.json`. The bytes at this commit are not held: git history holds the converted v1 (f64fe14).
