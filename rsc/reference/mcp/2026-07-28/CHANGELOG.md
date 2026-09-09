# mcp 2026-07-28 changelog

The 2026-07-28 lineage of the Model Context Protocol schema, held verbatim under `rsc/reference/mcp/2026-07-28/` at the upstream commit its `provenance.csv` rows pin (#587): one section per pin, newest first; the first section states the change from the lineage before it. A definition named here is the type of that name exported by `schema.ts` (`../generate.md` states the correspondence and the generation).

---

## 271ecc9accafdd9b83a3c869fa67c22953b2af80

Taken 2026-09-09 (reading-room) by `corpus-yoga reference sync`'s procedure from upstream's `schema/2026-07-28/` at commit `271ecc9accafdd9b83a3c869fa67c22953b2af80`, the newest commit touching that directory on upstream's main ("fix(schema): apply subscriptions/listen envelope and MetaObject rename", 2026-07-28); first held 2026-09-06 (#561, as `_reference/mcp` v3), moved here verbatim by #572 with `schema.ts` beside it. 155 definitions under `$defs`, `$schema` `https://json-schema.org/draft/2020-12/schema`; schema.json 181,474 bytes, SHA256 `ef70b61f99b6d2e5e3b46863822eab08dff6a45bedc7a08914e0e5b133f40203`; schema.ts 98,426 bytes, SHA256 `742750af0bb8c716e7030c4977c992b55d1adc4407e9e66997db5846baedc2cd`. `schema.json` is generated from `schema.ts` by upstream's generator (`../generate.md`; `corpus-yoga mcp reproduce` witnesses it). `rsc/schema/protocol/mcpMessage` is the house factoring derived from this lineage.

The reshape, read from `schema.ts` at this commit: a client sends requests and one notification and never a response - `ServerRequest` is gone, `ClientRequest` is the one request union (10 members), `ClientResult` is declared `= EmptyResult` and used nowhere, `ClientNotification` is the one message `notifications/cancelled`; the three exchanges a server initiates (`sampling/createMessage`, `elicitation/create`, `roots/list`) carry no `id` and no `jsonrpc` and travel inside an `InputRequiredResult` (`resultType` `input_required`, an `inputRequests` map keyed by server ids) returned to `tools/call`, `prompts/get` and `resources/read`, answered by the client retrying that request with `inputResponses` and `requestState`; `subscriptions/listen` is the one long-lived request, its result a stream of opt-in notifications (`SubscriptionFilter`) terminated on stdio by the server's cancelled notification; `server/discover` replaces `initialize`, every request's `_meta` carries `io.modelcontextprotocol/protocolVersion` and `clientCapabilities`, and `CacheableResult` states `cacheScope` and `ttlMs` on the pattern of HTTP `Cache-Control`. The Tasks family of 2025-11-25 is absent.

The protocol at this lineage, the first with one direction: the house layer rule partitions the 155 definitions as jsonrpc 38, agentic 36, session 28, resources 19, prompts 16, content 9, tools 9; against 2025-11-25 the kernel doubles (19 to 38: the typed result-response wrappers and the error catalogue), session falls (37 to 28: `initialize`, `ping` and `logging/setLevel` gone, `server/discover` and the subscription acknowledgement in), tasks vanishes (14 to 0), resources grow (14 to 19: the `subscriptions/listen` surface), agentic grows (31 to 36: the input-required round trip) - and the agentic layer changes kind, from a second wire direction to a continuation carried in results, as the reshape below reads.

### Replaces

2025-11-25

#### Restricted

- The wire loses a direction: `ServerRequest` is gone, a server sends requests to no one, and a client returns no result - `ClientResult` is declared and carried by nothing (`rsc/schema/protocol/mcpMessage/unreachable.csv`).
- `initialize` and `notifications/initialized`, `ping` and `logging/setLevel` are gone as methods; `resources/subscribe` and `resources/unsubscribe` are gone; Tasks is gone whole.
- `ClientNotification` shrinks to the one message `notifications/cancelled`.
- Methods gone: `initialize`, `logging/setLevel`, `notifications/elicitation/complete`, `notifications/initialized`, `notifications/roots/list_changed`, `notifications/tasks/status`, `ping`, `resources/subscribe`, `resources/unsubscribe`, `tasks/cancel`, `tasks/get`, `tasks/list`, `tasks/result`.
- Definition names absent (32): `CancelTaskRequest`, `CancelTaskResult`, `CreateTaskResult`, `ElicitationCompleteNotification`, `GetTaskPayloadRequest`, `GetTaskPayloadResult`, `GetTaskRequest`, `GetTaskResult`, `InitializeRequest`, `InitializeRequestParams`, `InitializeResult`, `InitializedNotification`, `ListTasksRequest`, `ListTasksResult`, `PingRequest`, `RelatedTaskMetadata`, `RootsListChangedNotification`, `ServerRequest`, `SetLevelRequest`, `SetLevelRequestParams`, `SubscribeRequest`, `SubscribeRequestParams`, `Task`, `TaskAugmentedRequestParams`, `TaskMetadata`, `TaskStatus`, `TaskStatusNotification`, `TaskStatusNotificationParams`, `ToolExecution`, `URLElicitationRequiredError`, `UnsubscribeRequest`, `UnsubscribeRequestParams`.

#### Relaxed

- `server/discover` - a server advertises its versions and capabilities on request, and every request's `_meta` carries `io.modelcontextprotocol/protocolVersion` and `clientCapabilities`, so a server can be stateless per request.
- The input-required round trip: `tools/call`, `prompts/get` and `resources/read` may return `InputRequiredResult` (`resultType` `input_required`, an `inputRequests` map of `CreateMessageRequest`, `ElicitRequest` or `ListRootsRequest`, none a wire message), and the client retries the request with `inputResponses` and `requestState`.
- `subscriptions/listen` - one long-lived request whose result is a stream of opt-in notifications (`SubscriptionFilter`), acknowledged by `notifications/subscriptions/acknowledged`, terminated on stdio by the server's own cancelled notification.
- A typed result response per request (`CallToolResultResponse`, `ReadResourceResultResponse`, ...), a typed error catalogue (`ParseError` to `MissingRequiredClientCapabilityError`), and `CacheableResult` (`cacheScope`, `ttlMs`) on the pattern of HTTP `Cache-Control`.
- Methods new: `notifications/subscriptions/acknowledged`, `server/discover`, `subscriptions/listen`.
- Definition names new (42): `CacheableResult`, `CallToolResultResponse`, `CompleteResultResponse`, `DiscoverRequest`, `DiscoverResult`, `DiscoverResultResponse`, `GetPromptResultResponse`, `HeaderMismatchError`, `InputRequest`, `InputRequests`, `InputRequiredResult`, `InputResponse`, `InputResponseRequestParams`, `InputResponses`, `InternalError`, `InvalidParamsError`, `InvalidRequestError`, `JSONArray`, `JSONObject`, `JSONValue`, `ListPromptsResultResponse`, `ListResourceTemplatesResultResponse`, `ListResourcesResultResponse`, `ListToolsResultResponse`, `MetaObject`, `MethodNotFoundError`, `MissingRequiredClientCapabilityError`, `NotificationMetaObject`, `ParseError`, `ReadResourceResultResponse`, `RequestMetaObject`, `ResultMetaObject`, `ResultType`, `SubscriptionFilter`, `SubscriptionsAcknowledgedNotification`, `SubscriptionsAcknowledgedNotificationParams`, `SubscriptionsListenRequest`, `SubscriptionsListenRequestParams`, `SubscriptionsListenResult`, `SubscriptionsListenResultMetaObject`, `SubscriptionsListenResultResponse`, `UnsupportedProtocolVersionError`.

#### Refactored

- The three exchanges a server initiates - `sampling/createMessage`, `elicitation/create`, `roots/list` - keep their names and their params, and travel inside results instead of on the wire: the agentic layer changes kind from a second JSON-RPC direction to a continuation.
- `MetaObject` and its request, notification and result forms are named as such.
