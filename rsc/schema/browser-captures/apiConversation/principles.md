---
schema_file: rsc/schema/browser-captures/apiConversation/v1.json
principles_file: rsc/schema/browser-captures/apiConversation/principles.md
workflow_file: rsc/schema/browser-captures/apiConversation/workflow.md
version: "1.0"
---

# Schema Design Principles for `rsc/schema/browser-captures/apiConversation/v{N}.json`

The generic schema design principles in [`rsc/schema/principles.md`](../../principles.md) apply
to this schema in full. Read that document first. This document records only the
adaptations specific to the live API conversation schema.

---

## Adaptations

### Diagnostic suite

All diagnostics pass with no pipeline-specific exceptions beyond the universal
versioned-schema skip (`naming.root_schema_title_matches_filename` — versioned filename
vs `apiConversation` title, same as all versioned schemas).

### Correspondence via model_join.csv

`rsc/schema/model_join.csv` is a unified four-way correspondence table covering all
pipeline schemas (conversations, session, apiConversation) and the MCP protocol.
One row per concept, one column per schema — full outer join semantics.

### `allOf` at root

All schemas use `allOf: [{$ref: "#/definitions/RootType"}]` at root rather than a
bare `$ref` — see `api.draft4_limitations` in [`rsc/schema/principles.md`](../../principles.md).
