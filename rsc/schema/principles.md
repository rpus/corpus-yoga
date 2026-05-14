# Schema Design Principles — All Pipelines

Generic design principles for all schemas in `rsc/schema/`. Each per-pipeline
`principles.md` defers to this document and records only its own deviations.

Each principle has a **status**:

- `enforced` — diagnostic script exists and must always pass; run by `src/test/pre_commit.py`
- `advisory` — worth checking; violations may be intentional
- `manual` — requires human judgement; no fully automatable check
- `informational` — context only; no check
- `open` — genuinely undecided; here for awareness and future discussion

---

## Naming

### `naming.upper_camel_case` · *enforced*

**All definition names are UpperCamelCase.**

UpperCamelCase for definition names cleanly distinguishes schema type names from data
field names (which are snake_case or lowercase). A `$ref` is always visually distinct
from a property key — e.g. `"uuid": {"$ref": "#/definitions/UuidV4"}` is unambiguous
at a glance.

```text
Diagnostic: src/test/diagnostics/naming.upper_camel_case.py
```

---

### `naming.title_matches_key` · *enforced*

**Every definition's `title` matches its key.**

The `title` field is the human-readable name. It should match the definition key exactly
so tooling (e.g. VS Code tooltips) shows the correct name.

```text
Diagnostic: src/test/diagnostics/naming.title_matches_key.py
Repair:     src/test/repairs/naming.title_matches_key.py
```

---

### `naming.root_schema_title_matches_filename` · *not applicable to versioned schemas*

**The root schema's `title` matches the schema filename stem.**

For non-versioned schemas (e.g. `model.json`) this is enforced by
`check_root_schema_diagnostics`. For versioned schemas the files are named `v1.json`,
`v2.json`, etc. — the filename stem is a version number, not the schema title — so the
diagnostic is universally skipped for all versioned schemas via `_UNIVERSAL_DIAG_SKIP`
in `src/test/pre_commit.py`.

---

### `naming.property_keys_lowercase` · *enforced*

**All property keys in data schemas are lowercase or snake\_case.**

Property keys mirror the actual JSON data fields. UpperCamelCase keys would indicate a
wrongly-renamed property.

```text
Diagnostic: src/test/diagnostics/naming.property_keys_lowercase.py
```

---

## Structure

### `structure.field_order` · *enforced*

**Every definition begins with `title`, `description`, `type` (in that order).**

Consistent field ordering makes schemas easier to scan. The only exception is the root
schema, which begins with `$schema`.

```text
Diagnostic: src/test/diagnostics/structure.field_order.py
Repair:     src/test/repairs/structure.field_order.py
```

---

### `structure.bfs_order` · *enforced*

**Definitions are ordered in breadth-first referential encounter order.**

Reading the definitions top-to-bottom should follow the same order as reading the schema
by following `$ref`s. Definitions unreachable via `$ref` appear at the end. BFS order
must be reapplied after any edit that adds or reorders definitions.

```text
Diagnostic: src/test/diagnostics/structure.bfs_order.py
Repair:     src/test/repairs/structure.bfs_order.py
```

---

### `structure.definitions_at_bottom` · *enforced*

**The `definitions` key is the last key in the root schema.**

The root schema header is read first; `definitions` is a reference section.

```text
Diagnostic: src/test/diagnostics/structure.definitions_at_bottom.py
Repair:     src/test/repairs/structure.definitions_at_bottom.py
```

---

### `structure.required_subset_of_properties` · *enforced*

**Every `required` field is listed in `properties`.**

A required field not present in `properties` is a schema error.

```text
Diagnostic: src/test/diagnostics/structure.required_subset_of_properties.py
```

---

### `structure.no_redundant_additional_properties_true` · *enforced*

**No explicit `additionalProperties: true`.**

`additionalProperties: true` is the default in draft-4. Explicit occurrences are
redundant. The meaningful values are `false` (closed) and absent (open).

```text
Diagnostic: src/test/diagnostics/structure.no_redundant_additional_properties_true.py
Repair:     src/test/repairs/structure.no_redundant_additional_properties_true.py
```

---

### `structure.all_definitions_reachable` · *enforced*

**Every definition is reachable from the root via `$ref`.**

Unreachable definitions are dead code.

```text
Diagnostic: src/test/diagnostics/structure.all_definitions_reachable.py
```

---

### `structure.no_dangling_refs` · *enforced*

**Every `$ref` target exists in `definitions`.**

```text
Diagnostic: src/test/diagnostics/structure.no_dangling_refs.py
```

---

### `structure.minItems_on_non_empty_arrays` · *enforced*

**Arrays that are never empty in observed data have `minItems: 1`.**

```text
Diagnostic: src/test/diagnostics/structure.minItems_on_non_empty_arrays.py
```

---

### `structure.pattern_constraints_enforced` · *enforced*

**String fields with known formats use `pattern` rather than documenting the regex only
in `description`.**

Draft-4 `"pattern"` is enforced by `jsonschema.Draft4Validator`. Regex patterns that are
documentation-only should be promoted to `"pattern"`.

```text
Diagnostic: src/test/diagnostics/structure.pattern_constraints_enforced.py
```

---

### `structure.property_order_matches_data` · *enforced*

**Properties within each schema appear in the same order as fields in the actual JSON data.**

```text
Diagnostic: src/test/diagnostics/structure.property_order_matches_data.py
```

---

## Documentation

### `documentation.every_definition_has_title_and_description` · *enforced*

**Every definition has both `title` and `description`.**

Titles and descriptions surface as VS Code tooltips via `rsc/schema/documenter.json`.

```text
Diagnostic: src/test/diagnostics/documentation.every_definition_has_title_and_description.py
Repair:     src/test/repairs/documentation.every_definition_has_title_and_description.py
```

---

### `documentation.null_only_fields_documented` · *enforced*

**Fields typed as `null` note this empirical observation in their description.**

A `null`-typed field is a strong empirical claim based on observed data only.

```text
Diagnostic: src/test/diagnostics/documentation.null_only_fields_documented.py
```

---

### `documentation.open_set_enums_documented` · *enforced*

**Enums that are likely open sets say so in their description.**

Exempt: single-value discriminators and known closed sets.

```text
Diagnostic: src/test/diagnostics/documentation.open_set_enums_documented.py
```

---

### `documentation.discriminator_fields_annotated` · *enforced*

**Discriminator fields are annotated with `description: "(discriminator)"`.**

Only checked on `type` and `name` properties referenced directly from a `oneOf`.

```text
Diagnostic: src/test/diagnostics/documentation.discriminator_fields_annotated.py
```

---

## Composition Patterns

### `composition.discriminated_union_pattern` · *manual*

**Discriminated unions follow the wrapper / base / subtype pattern.**

Three layers:

1. **Wrapper** — exactly five fields: `title`, `description`, `type`, `allOf` (base ref
   + `Has*DiscriminatorProperty` ref), `oneOf` (subtype refs).
2. **`...Base`** — `additionalProperties: false`, all shared fields; discriminator present
   but unconstrained.
3. **Subtypes** — discriminator constrained to a single `enum` value; per-subtype fields.

`allOf` and `oneOf` sit at the wrapper level, not inside subtypes, avoiding
`additionalProperties` conflicts.

---

### `composition.discriminator_values_disjoint` · *enforced*

**Discriminator enum values across all branches of a `oneOf` are mutually disjoint.**

```text
Diagnostic: src/test/diagnostics/composition.discriminator_values_disjoint.py
```

---

### `composition.base_schemas_closed` · *enforced*

**All `...Base` schemas have `additionalProperties: false`.**

The `...Base` schema is the definitive closed contract for all shared fields.

```text
Diagnostic: src/test/diagnostics/composition.base_schemas_closed.py
```

---

### `composition.wrapper_has_five_fields` · *enforced*

**Union wrapper schemas have exactly five fields: `title`, `description`, `type`, `allOf`, `oneOf`.**

```text
Diagnostic: src/test/diagnostics/composition.wrapper_has_five_fields.py
```

---

### `composition.no_additional_properties_on_subtypes` · *enforced*

**Subtype schemas must not combine `additionalProperties: false` with `allOf` referencing
a schema that has `properties`.**

This would cause the base's properties to be rejected as "additional". The constraint
belongs exclusively on the `...Base` schema.

```text
Diagnostic: src/test/diagnostics/composition.no_additional_properties_on_subtypes.py
```

---

### `composition.base_not_used_directly` · *enforced*

**`...Base` schemas are never referenced directly from `oneOf` lists.**

The base is an implementation detail of the wrapper.

```text
Diagnostic: src/test/diagnostics/composition.base_not_used_directly.py
```

---

## Draft-4 Limitations

### `api.draft4_limitations` · *informational*

**Known draft-4 limitations and workarounds used across all schemas.**

- **No `if`/`then`/`else`**: use the `allOf`/`oneOf` wrapper/base/subtype pattern.
- **`$ref` siblings are ignored**: move sibling documentation into the referenced
  definition's `description`. Use `allOf: [{$ref: ...}]` at root to avoid silencing
  `title`, `description`, and `definitions`.
- **No `nullable` shorthand**: use `oneOf: [{type: null}, ...]` or a named definition.
- **No `$comment`**: use `description` for all documentation including internal notes.
- **No cross-field constraints**: document in `description` with a verification snippet.
- **No `format` enforcement**: `format: date-time` is advisory only; use `pattern`.
- **`additionalProperties` on a base schema used in `allOf`** does not see properties
  defined in sibling schemas — a known limitation that affects base/subtype composition.

---

## Maintenance

### `maintenance.bfs_reorder_after_edits` · *enforced*

**Reapply BFS ordering after any structural edits.**

```text
Repair: src/test/repairs/structure.bfs_order.py
```

---

### `maintenance.verify_before_commit` · *manual*

**No change is committed until it has been tested and the result verified.**

For schema changes: validation outputs must be current and passing. For script changes:
the script must have been run against real data. For documentation changes: the document
must have been read through after the last edit.

The pre-commit hook enforces what it can mechanically but cannot substitute for human
verification.

---

### `maintenance.model_join_csv` · *manual*

**Review `rsc/schema/model_join.csv` whenever any schema changes.**

`model_join.csv` is the unified four-way field correspondence table (conversations ↔
session ↔ apiConversation ↔ MCP). Update it whenever a schema gains or loses a
definition with a notable counterpart in another schema. `src/test/pre_commit.sh`
validates all JSON Pointer fragments.
