# mcp 2024-11-05 changelog

The 2024-11-05 lineage of the Model Context Protocol schema, held verbatim under `rsc/reference/mcp/2024-11-05/` at the upstream commit its `provenance.csv` rows pin (#587): one section per pin, newest first; the first section states the change from the lineage before it. A definition named here is the type of that name exported by `schema.ts` (`../generate.md` states the correspondence and the generation).

---

## 93671a3f2bac3bc11b0eb6327c2d029e272b2871

Taken 2026-09-09 (reading-room) by `corpus-yoga reference sync`'s procedure from upstream's `schema/2024-11-05/` at commit `93671a3f2bac3bc11b0eb6327c2d029e272b2871`, the newest commit touching that directory on upstream's main (a dependency bump of 2026-06-29 that reformatted the files). The first dated lineage upstream published: 79 definitions under `definitions`, `$schema` `http://json-schema.org/draft-07/schema#`; schema.json 87,877 bytes, SHA256 `61cea2392d4f284092d09bc84b9ac488c0d5618ac2b38a56942fc5b99fd960ce`; schema.ts 31,186 bytes, SHA256 `8e87348b6c1a9de1ec7ac136f407b687521bcdeb357adedbf5367bfc19c18d38`.

The protocol at this lineage: a two-direction JSON-RPC wire - `ClientRequest` a union of 13, `ServerRequest` of 3 (`ping`, `sampling/createMessage`, `roots/list`), `ClientNotification` of 4, `ServerNotification` of 7, `ClientResult` of 3, `ServerResult` of 10 - opened by `initialize` and `notifications/initialized`; the methods by namespace are resources 5, prompts 2, tools 2, notifications 9, completion 1, sampling 1, roots 1, initialize 1, ping 1, logging 1. `schema.ts` carries no `@category` tags at this lineage, so the house layer rule (`rsc/schema/protocol/mcpMessage/category_layer.csv`, #595) does not apply; the reading is by method namespace and direction union alone.

### Replaces

None - the first dated lineage upstream published.

#### Restricted

None.

#### Relaxed

- Methods (24): `completion/complete`, `initialize`, `logging/setLevel`, `notifications/cancelled`, `notifications/initialized`, `notifications/message`, `notifications/progress`, `notifications/prompts/list_changed`, `notifications/resources/list_changed`, `notifications/resources/updated`, `notifications/roots/list_changed`, `notifications/tools/list_changed`, `ping`, `prompts/get`, `prompts/list`, `resources/list`, `resources/read`, `resources/subscribe`, `resources/templates/list`, `resources/unsubscribe`, `roots/list`, `sampling/createMessage`, `tools/call`, `tools/list`.
- Definition names (79): `Annotated`, `BlobResourceContents`, `CallToolRequest`, `CallToolResult`, `CancelledNotification`, `ClientCapabilities`, `ClientNotification`, `ClientRequest`, `ClientResult`, `CompleteRequest`, `CompleteResult`, `CreateMessageRequest`, `CreateMessageResult`, `Cursor`, `EmbeddedResource`, `EmptyResult`, `GetPromptRequest`, `GetPromptResult`, `ImageContent`, `Implementation`, `InitializeRequest`, `InitializeResult`, `InitializedNotification`, `JSONRPCError`, `JSONRPCMessage`, `JSONRPCNotification`, `JSONRPCRequest`, `JSONRPCResponse`, `ListPromptsRequest`, `ListPromptsResult`, `ListResourceTemplatesRequest`, `ListResourceTemplatesResult`, `ListResourcesRequest`, `ListResourcesResult`, `ListRootsRequest`, `ListRootsResult`, `ListToolsRequest`, `ListToolsResult`, `LoggingLevel`, `LoggingMessageNotification`, `ModelHint`, `ModelPreferences`, `Notification`, `PaginatedRequest`, `PaginatedResult`, `PingRequest`, `ProgressNotification`, `ProgressToken`, `Prompt`, `PromptArgument`, `PromptListChangedNotification`, `PromptMessage`, `PromptReference`, `ReadResourceRequest`, `ReadResourceResult`, `Request`, `RequestId`, `Resource`, `ResourceContents`, `ResourceListChangedNotification`, `ResourceReference`, `ResourceTemplate`, `ResourceUpdatedNotification`, `Result`, `Role`, `Root`, `RootsListChangedNotification`, `SamplingMessage`, `ServerCapabilities`, `ServerNotification`, `ServerRequest`, `ServerResult`, `SetLevelRequest`, `SubscribeRequest`, `TextContent`, `TextResourceContents`, `Tool`, `ToolListChangedNotification`, `UnsubscribeRequest`.

#### Refactored

None.
