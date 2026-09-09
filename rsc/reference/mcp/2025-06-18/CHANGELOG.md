# mcp 2025-06-18 changelog

The 2025-06-18 lineage of the Model Context Protocol schema, held verbatim under `rsc/reference/mcp/2025-06-18/` at the upstream commit its `provenance.csv` rows pin (#587): one section per pin, newest first; the first section states the change from the lineage before it. A definition named here is the type of that name exported by `schema.ts` (`../generate.md` states the correspondence and the generation).

---

## 2ebb8060268e177b22598b403d6ba6764bb899ac

Taken 2026-09-09 (reading-room) by `corpus-yoga reference sync`'s procedure from upstream's `schema/2025-06-18/` at commit `2ebb8060268e177b22598b403d6ba6764bb899ac`, the newest commit touching that directory on upstream's main (upstream's fix of 2026-07-27 retyping `NumberSchema`'s bounds from integer to number in the generated JSON). 91 definitions under `definitions`, `$schema` `http://json-schema.org/draft-07/schema#`; schema.json 108,234 bytes, SHA256 `af845e7e5b9d27107d1690f0936022546177a1403e63ffb11470135b296a2e01`; schema.ts 42,430 bytes, SHA256 `7d7f4cc6f3adb76e3fd5e1eee6bab8b1e183cfaf719da66d2aa5661737ca9539`.

The protocol at this lineage: the two-direction wire grows one server request - `ServerRequest` a union of 4 (`ping`, `sampling/createMessage`, `roots/list` and the new `elicitation/create`), `ClientResult` of 4, `ClientRequest` 13, `ClientNotification` 4, `ServerNotification` 7, `ServerResult` 10 - still opened by `initialize`. `@category` tags begin here, on 79 of 91 declarations (the seven exported constants aside), and the house layer rule (`rsc/schema/protocol/mcpMessage/category_layer.csv` with `placement.csv`'s rows for this lineage, #595) partitions the 91 definitions as session 25, jsonrpc 15, agentic 15, prompts 11, resources 10, content 9, tools 6 - the agentic layer being sampling, roots and the first elicitation, each a server request with its own client result.

### Replaces

2025-03-26

#### Restricted

- JSON-RPC batching is gone: a message is one request, notification or response, never an array of them.
- Definition names absent (3): `JSONRPCBatchRequest`, `JSONRPCBatchResponse`, `ResourceReference`.

#### Relaxed

- `elicitation/create` - the server may ask the user, through the client, for structured input against a small primitive schema (`StringSchema`, `NumberSchema`, `BooleanSchema`, `EnumSchema`); `ServerRequest` grows from 3 to 4 and `ClientResult` with it.
- `ContentBlock` gathers the content kinds a message may carry, and `ResourceLink` joins them.
- Methods new: `elicitation/create`.
- Definition names new (11): `BaseMetadata`, `BooleanSchema`, `ContentBlock`, `ElicitRequest`, `ElicitResult`, `EnumSchema`, `NumberSchema`, `PrimitiveSchemaDefinition`, `ResourceLink`, `ResourceTemplateReference`, `StringSchema`.

#### Refactored

- `ResourceReference` becomes `ResourceTemplateReference`, naming what it references.
