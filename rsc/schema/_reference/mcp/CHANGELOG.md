# mcp reference-snapshot changelog

This family is a VERBATIM UPSTREAM SNAPSHOT, not a house schema: the Model
Context Protocol spec, byte-for-byte as upstream publishes it (#561 retired
the draft-04 conversion v1 and v2 carried). `model_join.csv`'s `mcp_path`
column points into it spelling the file's own container (`#/$defs/…` from
v3; `#/definitions/…` was the converted spelling). No data is validated
against it (it enters no pipeline, no coverage or frontier gate), and the
house style diagnostics deliberately skip `_reference/` families - repairing
upstream text to satisfy house rules would falsify the snapshot. A verbatim
file carries no description of its own, so from v3 each version's changelog
section carries its provenance: the upstream raw URL, the commit it was
taken from, and the upstream file's SHA256 (v1 and v2 carried the same
triple in their doctored `description` fields). `check_mcp_schema` reads the
latest section's triple, holds the committed file to the SHA256 (the
verbatim witness, hermetic), and - network permitting - compares the live
URL and upstream's newest dated `schema/` directory against it. When
upstream drifts or opens a new dated lineage, mint the next version in the
old one's place: the latest version is the schema and the rest history
(#557) - the superseded file is deleted, its content in git and its
narrative here.

---

## v3

Upstream versions the spec by dated directory (`schema/<date>/schema.json`),
minting a new directory and freezing the old: the 2025-11-25 lineage v1 and
v2 tracked has ended, and 2026-07-28 is the newest dated directory (listed
2026-09-06). The snapshot follows, and the conversion retires with the move
(#561): v3 is upstream's file byte-for-byte - `$defs`, 2020-12 `$schema`,
no description. The conversion had been dialect-partial all along: 93
`const` keywords (draft-06 vocabulary) survived verbatim in v2 under a
description claiming draft-04 - 37 `jsonrpc: "2.0"` pins, 31 `method` pins,
20 `type` discriminators - each vacuous to a draft-04 validator, which
ignores unknown keywords.

Provenance:

- upstream: <https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/refs/heads/main/schema/2026-07-28/schema.json>
- as at commit: `271ecc9accafdd9b83a3c869fa67c22953b2af80`
- upstream SHA256: `ef70b61f99b6d2e5e3b46863822eab08dff6a45bedc7a08914e0e5b133f40203`

155 definitions (v2 held 145). Every `model_join.csv` `mcp_path` pointer
resolves against v3 with its container respelled `#/$defs/…`, and every
identity-class join edge holds unchanged.

Disposal (#558's rule - the latest version is the schema, the rest
history): v2.json deleted with this mint - 1 file, 141,084 bytes,
reading-room, 2026-09-06; its content is git history and its section below
stands.

### Replaces

v2

#### Restricted

- 32 definition names of the 2025-11-25 lineage are absent from 2026-07-28
  (the Tasks family, the Subscribe/Unsubscribe pair, `InitializeRequest`
  and other concrete request wrappers) - a name-level fact of upstream's
  reshape, not a house adjudication; no house datum validates against this
  family, and no `model_join.csv` pointer names any of them.

#### Relaxed

- 42 definition names are new in 2026-07-28 (`DiscoverRequest`, the
  `*ResultResponse` wrappers, the JSON-RPC error catalogue, the
  subscriptions surface) - name-level, as above.

#### Refactored

- The snapshot's own dialect: v2 spelled upstream in converted draft-04
  (`definitions`, rewritten refs); v3 spells upstream verbatim (`$defs`,
  2020-12 `$schema`). Same protocol content where the lineages agree; the
  `mcp_path` column respells its container to match.

## v2

Upstream fixed its own generator: commit `c4c367f` ("schema: fix 2025-11-25
NumberSchema min/max/default to number in generated JSON") retypes
`NumberSchema.minimum` / `.maximum` / `.default` from `integer` to `number` —
three lines, nothing else. The snapshot follows: same conversion as v1
(`$defs` → `definitions`, refs rewritten, draft-04 `$schema`), proven by
reproducing v1 byte-for-byte from the old upstream before converting the new.
Every definition name survives, so every `model_join.csv` `mcp_path` pointer
resolves against v2 unchanged.

### Replaces

v1

#### Restricted

None.

#### Relaxed

- `NumberSchema.minimum` / `.maximum` / `.default` — `integer` → `number`,
  upstream's own correction; a fractional bound or default is now admitted,
  as the protocol always intended.

#### Refactored

None.

## v1

The MCP schema of 2025-11-25, taken at upstream commit `357adac` and converted
to draft-04. Lived as a single flat file beside this family (no versions, no
changelog, updated in place) until 2026-07-10, when the reference joined the
versioned-family system (same grammar as every other `model_join` column:
`_reference/mcp#/definitions/…`, resolved against the latest version).
