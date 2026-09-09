# mcpMessage changelog

This family is the HOUSE FACTORING of the Model Context Protocol schema (#562,
#598): the composition upstream's generator flattens, stated once in draft-04,
generated from upstream's `schema.ts` alone. It is a committed derivation, never
hand-edited: `corpus-yoga mcp sync` reads the newest lineage's `schema.ts` under
`rsc/reference/mcp` (whose `provenance.csv` pins the lineage, commit and SHA256)
through the parser generated from the house TypeScript grammar into the flat
shape of every declaration, one stated rule per TypeScript form
(`src/main/mcp/mcp_generation.py`), composes it over the extends clauses and tags
it by the categories `src/main/mcp/mcp_extraction.py` reads (#581, #595; the two
tables faced under `tmp/cache/mcp/`), and applies the hand-written tables beside
this file: `description.csv`, house text for the definitions schema.ts leaves
without a JSDoc; `unreachable.csv`, the definitions no message carries (#588);
`layer.csv`, the layers the protocol reads by, one row each with its reading -
jsonrpc, session, resources, tools, prompts, content, agentic, tasks - the closed
vocabulary; `category_layer.csv`, the house's reading of the `@category` tags into
those layers; `placement.csv`, the definitions neither the tag nor the composition
places, each with its reason (#595); and `addition.csv`, where the house reads
differently from upstream at a JSON Pointer - the null upstream's generator drops
from `JSONValue`, the protocol version pinned on the `_meta` field that names it
(#598). Every extends row is verified against the generated shapes before use, the
derivation refuses an unreachable table that disagrees with the wire, a
definition no rule places, and an addition row that fits neither reading, and
every description ends with its layer. One instance is one JSON-RPC message; the
root is the house definition `MCPMessage`, which admits exactly what the wire
admits. Upstream's `schema.json` is the witness, never a source: the dev gate
holds the version file byte-identical to the derivation (`mcp.factoring_current`)
and every upstream definition equal to its house counterpart resolved and
normalized, the declared additions set back (`mcp.factoring_agrees`). No data is
validated against it; every house diagnostic holds over it,
`structure.all_definitions_reachable` reading `unreachable.csv`.

---

## v5

Generated 2026-09-09 (reading-room) from `rsc/reference/mcp/2026-07-28/schema.ts`
alone, at commit `271ecc9accafdd9b83a3c869fa67c22953b2af80`, unchanged - upstream's
`schema.json` beside it now the witness and no longer a source (#598). Every
declaration is read through the house TypeScript grammar into the flat shape
upstream's generator would give it (`src/main/mcp/mcp_generation.py`, one rule per
TypeScript form), and composed as before; the alias rows retire, since every type
alias is a reference wherever schema.ts uses it, by construction. What upstream's
generator drops is carried by declaration (`addition.csv`): `JSONValue` admits
`null`, as `JSONValue` declares, and `io.modelcontextprotocol/protocolVersion` in
`RequestMetaObject` is pinned to `2026-07-28`, the `LATEST_PROTOCOL_VERSION`
schema.ts exports and no JSON of upstream's carries. 161 definitions, as v4; the
witness agrees on every one, the two additions set back.

### Replaces

v4

#### Restricted

- `RequestMetaObject.io.modelcontextprotocol/protocolVersion` - `enum
  ["2026-07-28"]`: a request naming another protocol version is refused, as the
  wire refuses it (`UnsupportedProtocolVersionError`); v4 admitted any string.

#### Relaxed

- `JSONValue` - admits `null` beside string, integer, boolean, object and array,
  as schema.ts declares it; v4 followed upstream's generator, which drops it.

#### Refactored

- Every definition's properties stand in schema.ts's declaration order, and every
  union's members in schema.ts's order (v4 followed upstream's generator:
  alphabetical properties, members by declaration of the member types) - 110
  definitions differ by order alone.
- `SamplingMessage.content` and `SubscriptionsListenResult.resultType` reference
  the aliases schema.ts names (`SamplingMessageContentBlock`, `ResultType`) where v4
  carried the spliced members and the bare string upstream inlined.
- `EmptyResult` carries its own JSDoc ("A result that indicates success but
  carries no data.") where v4 carried its target's; `ClientNotification` and
  `ClientResult`, aliases without a JSDoc, take house text from `description.csv`.
- The family description names the generation, the witness and `addition.csv`.

## v4

Derived 2026-09-09 (reading-room) from the same snapshot as v3 - lineage 2026-07-28
at commit `271ecc9accafdd9b83a3c869fa67c22953b2af80`, unchanged. What changed is
that every definition now carries its layer (#595). The derivation extracts the
`@category` tag schema.ts carries on 135 of its 155 declarations
(`tmp/cache/mcp/category.csv`, the third extracted table), reads it into the house
layers (`layer.csv`, one row per layer with its reading) by `category_layer.csv`
- a method tag by its first path segment, a named tag as itself - places an untagged definition by its alias target, its union members or
its descendants when they agree, and places the residue by `placement.csv`, each
row with its reason: the naming and pagination and caching bases whose descendants
span layers (`BaseMetadata`, `Icons`, `CacheableResult`, `PaginatedRequest`,
`PaginatedResult`), the direction unions (`ClientRequest`, `ServerResult`), the
continuation's unreferenced params (`InputResponseRequestParams`), and the five
house definitions. A definition none of these place refuses the derivation; a
placement for one the rule places refuses as a restatement. Every description ends
with `Layer: <layer>.`, so the version file reads by concern - jsonrpc 44 (the
JSON-RPC kernel: envelopes and headers, the common types, the error objects and
their wrappers, the root), agentic 36 (sampling, elicitation, roots and the
input-required round trip), session 28 (discover and capabilities, notifications,
pagination, caching, naming), resources 19 (resources and subscriptions), prompts
16 (prompts and completion), content 9, tools 9 - and the bare `corpus-yoga mcp`
reports the partition. 161 definitions, as v3. The diff is 324 lines: one clause
per description, the root's among them, and the family description naming the three
tables.

### Replaces

v3

#### Restricted

None. A description validates nothing.

#### Relaxed

None.

#### Refactored

- Every definition's description ends with its layer clause; the family
  description names `layer.csv`, `category_layer.csv` and `placement.csv`.

## v3

Derived 2026-09-09 (reading-room) from the same snapshot as v2 - lineage 2026-07-28
at commit `271ecc9accafdd9b83a3c869fa67c22953b2af80`, unchanged. What changed is
the rule for the root's wrappers (#588): a party's result union gets a `Response`
wrapper only when the other party declares requests, since a party's results
answer the other party's requests. schema.ts declares no `ServerRequest`, so no
message carries a `ClientResult`: in this lineage the exchanges a server
initiates (`sampling/createMessage`, `elicitation/create`, `roots/list`) carry no
`id` and no `jsonrpc` - they travel inside an `InputRequiredResult` returned to
`tools/call`, `prompts/get` and `resources/read`, and the client answers by
retrying that request with `inputResponses`. A client sends requests and one
notification, never a response. `ClientResultResponse`, which v1 minted to give
`ClientResult` a message, described a message no party can send; it leaves.
`ClientResult` stands as the snapshot declares it, a result no message carries,
declared so in `unreachable.csv` beside this file - the table
`structure.all_definitions_reachable` reads, and which the derivation refuses to
disagree with (an uncarried result union it does not name, a name it declares that
the root reaches). 161 definitions (v2: 162); `MCPMessage` has 19 branches (v2:
20).

### Replaces

v2

#### Restricted

None. The same instances are admitted: an identified header whose `result` is a
bare `Result` is `JSONRPCResultResponse`'s shape, which `JSONRPCMessage` carries.

#### Relaxed

None.

#### Refactored

- `ClientResultResponse` - removed, with its branch of `MCPMessage`.
- `ClientResult` - unreferenced, so it stands last: definitions keep breadth-first
  order from the root, the unreachable after.
- The root's description names the wrappers as those of "the result and error
  unions a party sends"; the family's description names `unreachable.csv`.

## v2

Derived 2026-09-08 (home-room) from the same snapshot as v1 - lineage 2026-07-28
at commit `271ecc9accafdd9b83a3c869fa67c22953b2af80`, unchanged. What changed is
where the derivation's inputs come from (#581): the composition and alias tables
are extracted from the committed `schema.ts` by stated rules and faced under
`tmp/cache/mcp/`, and the two hand-written tables left this directory. The rules
reproduce every hand row - 90 extends rows over 80 definitions, 10 alias rows -
and find two more the hand had not written: `EmptyResult` is declared
`export type EmptyResult = Result` (a copy site; v1 already read it as a
reference, so no change), and `JSONRPCMessage` lists `JSONRPCResponse` as a
member, which the generator had inlined as its two members. 162 definitions, as
v1; the root description names the extraction where v1 named the hand tables.

### Replaces

v1

#### Restricted

None.

#### Relaxed

None.

#### Refactored

- `JSONRPCMessage` - `anyOf` of `JSONRPCRequest`, `JSONRPCNotification` and
  `JSONRPCResponse`, as schema.ts declares it; v1 spelled the response's two
  members inline. `JSONRPCResponse` is thereby referenced and leaves the root's
  branch list: `MCPMessage` has 20 branches (v1: 21). The same instances are
  admitted. Definitions stand in breadth-first order from the root, so the
  order shifts where `JSONRPCResponse` is now reached.

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
  The row stands as schema.ts states it; the definition stands flat, and
  `corpus-yoga mcp` reports the override.

Every `const` is spelled as draft-04's one-element `enum`; every `$defs` ref as
`#/definitions/`; every enum of more than one value states the values as
exhaustive, the spec's closed sets. 24 definitions take their description
from `description.csv`. Definitions stand in breadth-first order from the root.
