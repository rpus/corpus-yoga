---
schema_file: rsc/schema/browser-captures/apiConversation/v1.json
principles_file: rsc/schema/browser-captures/apiConversation/principles.md
workflow_file: rsc/schema/browser-captures/apiConversation/workflow.md
version: "1.0"
---

# Schema Design Principles for `rsc/schema/browser-captures/apiConversation/v{N}.json`

The general schema design principles in `rsc/schema/chat-exports/conversations/principles.md` apply
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

The root schema uses `allOf: [{$ref: "#/definitions/ApiConversation"}]` rather than
a bare `$ref`. In JSON Schema draft-4, a bare `$ref` causes all sibling keywords
(`title`, `description`, `definitions`) to be silently ignored; `allOf` wrapping
avoids this.
