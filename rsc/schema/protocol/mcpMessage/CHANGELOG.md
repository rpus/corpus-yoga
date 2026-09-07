# mcpMessage changelog

This family is the HOUSE FACTORING of the Model Context Protocol schema (#562):
the composition upstream's generator flattens, stated once in draft-04. It is a
committed derivation, never hand-edited: `corpus-yoga protocol sync` derives the latest
version from the verbatim snapshot (`rsc/schema/_reference/mcp`, whose changelog
pins the lineage, commit and SHA256) and from three tables in
`rsc/schema/protocol/mcpMessage/` - `composition.csv`, the (definition, base) rows
of upstream's schema.ts `extends` at the pinned commit; `alias.csv`, where
schema.ts uses a type alias the generator inlined; `description.csv`, house text
for the definitions the snapshot leaves undescribed - every row verified against
the snapshot before use. One instance is one JSON-RPC message; the root is the
house definition `MCPMessage`. The dev gate holds the version file byte-identical
to the derivation (`protocol.factoring_current`) and every snapshot definition
equal to its house counterpart resolved and normalized (`protocol.factoring_agrees`).
No data is validated against it; every house diagnostic holds over it without
exception.

---

## v1

Derived 2026-09-07 (reading-room) from snapshot v3 - upstream lineage
2026-07-28 at commit `271ecc9accafdd9b83a3c869fa67c22953b2af80`, schema.json
SHA256 `ef70b61f99b6d2e5e3b46863822eab08dff6a45bedc7a08914e0e5b133f40203`;
structural reference schema.ts at the same commit.

162 definitions: the snapshot's 155 and 7 house definitions -
`JSONRPCHeader` (the `jsonrpc: "2.0"` pin) and `JSONRPCIdentifiedHeader` (header
plus `id`), the two bases upstream never names; `MCPMessage`, the root; and
`ClientResultResponse`, `ServerResultResponse`, `ProtocolError`,
`ProtocolErrorResponse`, the wrappers that give upstream's unreferenced result
and error unions their message. 85 definitions are composed over bases by
`allOf`, from 90 schema.ts rows. The envelope reads as schema.ts states it:
`JSONRPCRequest` is the identified header plus `Request`, `JSONRPCNotification`
the header plus `Notification`, `ListToolsRequest` a `PaginatedRequest` with its
method pinned, `ListToolsResult` a `CacheableResult` and `PaginatedResult` with
its `tools`.

`MCPMessage` has 21 branches: every message-shaped definition upstream
exports but no definition references (`JSONRPCMessage`, `JSONRPCResponse`, the
direction unions, the typed result responses, the typed error responses) and
the three house wrappers. Every branch is a `JSONRPCMessage`, so the root admits
exactly what the wire admits, and every definition is reachable from it -
`structure.all_definitions_reachable` holds with no skip.

10 alias rows revive the type aliases the generator inlined and left
dead: `Cursor` (the pagination cursors), `ResultType` (`Result.resultType`),
`EmptyResult` (`ClientResult`, `ServerResult`'s first branch), `JSONArray`
(`JSONValue`'s array branch), `EnumSchema` and its two halves
(`PrimitiveSchemaDefinition`'s enum branches), and `ClientNotification`, which
upstream emitted as a whole copy of `CancelledNotification`.

Two divergences from schema.ts, both forced by JSON Schema's `allOf`, which
conjoins and cannot narrow:

- A concrete message extends the header that fits it (`JSONRPCIdentifiedHeader`
  for requests and result responses, `JSONRPCHeader` for notifications and
  error responses), not the generic `JSONRPCRequest` or `JSONRPCNotification`
  whose open `params` it narrows to a `$ref`; the derivation realizes each
  declared envelope base by its header.
- `SubscriptionsListenResult extends Result` is an override: it narrows `_meta`
  to `SubscriptionsListenResultMetaObject`, a different `$ref` from `Result`'s.
  The row stays in `composition.csv` as schema.ts states it; the definition
  stands flat, and `corpus-yoga protocol` reports the override.

Every `const` is spelled as draft-04's one-element `enum`; every `$defs` ref as
`#/definitions/`; every enum of more than one value states the values as
exhaustive, the spec's closed sets. 24 definitions take their description
from `description.csv`. Definitions stand in breadth-first order from the root.
