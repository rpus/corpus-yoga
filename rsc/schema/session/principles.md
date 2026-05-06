---
schema_file: rsc/schema/session/v1.json
principles_file: rsc/schema/session/principles.md
workflow_file: rsc/schema/session/workflow.md
version: "1.0"
---

# Schema Design Principles for `rsc/schema/session/v{N}.json`

The general schema design principles in `rsc/schema/conversations/principles.md` apply
to this schema in full. Read that document first. This document records only the
adaptations and known deviations that are specific to the CLI sessions schema.

---

## Adaptations

### Shared diagnostic suite

The diagnostic scripts in `src/test/diagnostics/` can be applied to this schema
directly. They have been generalised to use the first definition as the BFS/reachability
root, so they are not hardcoded to `Conversation`.

All diagnostics pass except:

- `naming.root_schema_title_matches_filename` — expected by design (versioned filename
  vs `sessions` title, same as the conversations schema versioned files)
- `composition.base_schemas_closed` — known deviation; see below

For empirical investigation and debugging:

- Use `src/test/code-projects/survey_code_session.py` before schema changes
- Use `src/test/code-projects/debug_code_session_record.py` to diagnose validation failures
- Run `src/test/pre_commit.sh` to validate `model_join.csv` pointer integrity

### Correspondence via model_join.csv

`rsc/schema/model_join.csv` is a unified four-way correspondence table covering all
pipeline schemas (conversations, session, apiConversation) and the MCP protocol.
One row per concept, one column per schema — full outer join semantics.
Update `model_join.csv` whenever `v1.json` changes — see `workflow.md` for the trigger
conditions.

---

## Known Deviations

### `TurnBase` — `additionalProperties: false` absent · *justified*

**Principle violated:** `composition.base_schemas_closed` — all `...Base` schemas
should have `additionalProperties: false`.

**Reason:** In JSON Schema draft-4, `additionalProperties` on a schema used in `allOf`
does not see properties defined in sibling schemas. `TurnBase` is used in:

```json
"UserTurn": {
  "allOf": [{ "$ref": "TurnBase" }, { "$ref": "HasTypeDiscriminatorProperty" }],
  "oneOf": [{ "$ref": "UserTurnType" }]
}
```

If `TurnBase` had `additionalProperties: false` with only its envelope properties,
it would reject the type-specific fields (`message`, `promptId`, `permissionMode`, etc.)
defined in `UserTurnType` — because draft-4 does not merge `properties` across `allOf`
before evaluating `additionalProperties`.

The conversations schema avoids this by putting ALL properties (shared and
type-specific) into the `...Base` schema. For the CLI sessions schema, the turn
types have enough distinct optional fields that a single comprehensive base would
be unwieldy. The envelope is documented in `TurnBase`; the type-specific fields
are in the subtype schemas; `additionalProperties: false` is deliberately absent
from `TurnBase`.

**Where closed:** All non-composition schemas are closed where possible
(`QueueOperation`, `PermissionModeRecord`, `LastPromptRecord`, `FileHistorySnapshot`,
`AiTitleRecord`, `AssistantMessage`, all content block schemas).

---

## Empirical Grounding Notes

The CLI sessions schema was derived from two sessions of one project. The
`empirical.validate_against_all_known_exports` principle applies — the schema must
validate all sessions in `../code-projects/` — but the corpus is small and likely
to surface new fields as more projects and Claude Code versions are observed.

Fields typed as `["null", "object"]` or `["string", "object"]` where only one form
has been sampled are flagged in `CHANGELOG.md` as open questions. Resolve them
by surveying additional sessions with `src/test/code-projects/survey_code_session.py`.
