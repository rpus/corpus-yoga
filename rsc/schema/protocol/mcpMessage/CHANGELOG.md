# mcpMessage changelog

This family is the HOUSE FACTORING of the Model Context Protocol schema (#562):
the composition upstream's generator flattens, stated once in draft-04. It is a
committed derivation, never hand-edited: `corpus-yoga protocol sync` derives the latest
version from the verbatim snapshot (`rsc/schema/_reference/mcp`, whose changelog
pins the lineage, commit and SHA256) and from two tables in
`rsc/schema/protocol/mcpMessage/` -
`composition.csv`, the (definition, base) rows transcribed from upstream's
schema.ts at the pinned commit, each verified against the snapshot before use,
and `description.csv`, house text for the definitions the snapshot leaves
undescribed. One instance is one JSON-RPC message; the root is JSONRPCMessage.
The dev gate holds the version file byte-identical to the derivation
(`protocol.factoring_current`) and every snapshot definition equal to its house
counterpart flattened and normalized (`protocol.factoring_agrees`). No data is
validated against it. The family skips `structure.all_definitions_reachable`
(`diagnostic_skip.json`): upstream publishes typed response wrappers, an error
catalogue and the direction unions that no definition references, and the
factoring keeps every upstream definition for its witness.

---

## v1

Derived 2026-09-06 (reading-room) from snapshot v3 - upstream lineage
2026-07-28 at commit `271ecc9accafdd9b83a3c869fa67c22953b2af80`, schema.json
SHA256 `ef70b61f99b6d2e5e3b46863822eab08dff6a45bedc7a08914e0e5b133f40203`;
structural reference schema.ts at the same commit.

157 definitions: the snapshot's 155 and two bases upstream never names -
`JSONRPCHeader` (the `jsonrpc: "2.0"` pin) and `JSONRPCIdentifiedHeader`
(header plus `id`). 82 definitions are composed over bases by `allOf`; 94
composition rows hold. The envelope reads as schema.ts states it:
`JSONRPCRequest` is the identified header plus `Request`, `JSONRPCNotification`
the header plus `Notification`, `ListToolsRequest` a `PaginatedRequest` with its
method pinned, `ListToolsResult` a `CacheableResult` and `PaginatedResult` with
its `tools`.

Two divergences from schema.ts, both forced by JSON Schema's `allOf`, which
conjoins and cannot narrow:

- A concrete message extends the header that fits it (`JSONRPCIdentifiedHeader`
  for requests and result responses, `JSONRPCHeader` for notifications and
  error responses), not the generic `JSONRPCRequest` or `JSONRPCNotification`
  whose open `params` it narrows to a `$ref`. The table's envelope rows say so.
- `SubscriptionsListenResult extends Result` is not bearable: it narrows `_meta`
  to `SubscriptionsListenResultMetaObject`, a different `$ref` from `Result`'s.
  The row is absent from `composition.csv` and the definition stands flat.

Every `const` is spelled as draft-04's one-element `enum`; every `$defs` ref as
`#/definitions/`; every enum of more than one value states the values as
exhaustive, the spec's closed sets. 24 definitions take their description from
`description.csv`. Definitions stand in breadth-first order from the root, the
unreferenced after them.
