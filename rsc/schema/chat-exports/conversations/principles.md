---
schema_file: rsc/schema/chat-exports/conversations/v6.json
principles_file: rsc/schema/chat-exports/conversations/principles.md
workflow_file: rsc/schema/chat-exports/conversations/workflow.md
version: "1.3"
---

# Schema Design Principles for `rsc/schema/chat-exports/conversations/v{N}.json`

A living document of design principles, diagnostics, and repairs for `rsc/schema/chat-exports/conversations/v{N}.json`. Each enforced principle has a machine-runnable diagnostic script in `src/test/diagnostics/` and (where automatable) a repair script in `src/test/repairs/`. Inline snippets are provided for advisory and manual principles, and for context where the script alone is not self-explanatory.

This document should be kept updated in parallel with the schema, the atomic scripts, and validation runs. The pre-commit hook (`src/test/pre_commit.py`) runs all enforced diagnostics automatically.

Principles are organised into eight categories: [Naming](#naming), [Structure](#structure), [Documentation](#documentation), [Empirical Grounding](#empirical-grounding), [Composition Patterns](#composition-patterns), [API Correspondence](#api-correspondence), [Integrity Constraints](#integrity-constraints), and [Open Questions](#open-questions). A final [Maintenance Workflow](#maintenance-workflow) section collects operational procedures.

Each principle has a **status**:

- `enforced` — diagnostic script exists and must always pass; run by `src/test/pre_commit.py`
- `advisory` — worth checking; violations may be intentional
- `manual` — requires human judgement; no fully automatable check
- `informational` — context only; no check
- `open` — genuinely undecided; no principle yet established; here for awareness and future discussion

---

## Naming

### `naming.upper_camel_case` · *enforced*

**All definition names are UpperCamelCase.**

Consistent UpperCamelCase for definition names cleanly distinguishes schema type names from data field names (which are snake_case). This means a `$ref` is always visually distinct from a property key — e.g. `"uuid": {"$ref": "#/definitions/UuidV4"}` is unambiguous at a glance.

```text
Diagnostic: src/test/diagnostics/naming.upper_camel_case.py
```

---

### `naming.title_matches_key` · *enforced*

**Every definition's `title` matches its key.**

The `title` field is the human-readable name of the schema. It should match the definition key exactly so that tooling (e.g. VS Code tooltips) shows the correct name.

```text
Diagnostic: src/test/diagnostics/naming.title_matches_key.py
Repair:     src/test/repairs/naming.title_matches_key.py
```

---

### `naming.root_schema_title_matches_filename` · *not applicable to versioned schemas*

**The root schema's `title` matches the schema filename stem (without extension).**

For non-versioned schemas (e.g. `data-table.json`, `model.json`) this is enforced by
`check_root_schema_diagnostics`. For versioned schemas the files are named `v1.json`,
`v2.json`, etc. — the filename stem is a version number, not the schema title — so the
diagnostic is universally skipped for all versioned schemas via `_UNIVERSAL_DIAG_SKIP`
in `src/test/pre_commit.py`. The title `"conversations"` is maintained by convention.

This principle was discovered during active development when the root title was
`"Claude Conversation Export"` rather than `"conversations"`.

---

### `naming.property_keys_lowercase` · *enforced*

**All property keys in data schemas are lowercase or snake\_case.**

Property keys mirror the actual JSON data fields, which follow snake\_case. UpperCamelCase keys would indicate a wrongly-renamed property — a bug encountered during the `timestamp`/`flags`/`display_content` renaming, where the rename script accidentally capitalised property keys as well as definition keys.

```text
Diagnostic: src/test/diagnostics/naming.property_keys_lowercase.py
```

---

### `naming.subtype_naming_convention` · *advisory*

**Tool block subtypes are named `{ToolName}ToolUseBlock` / `{ToolName}ToolResultBlock`.**

The tool name is converted from snake\_case to UpperCamelCase and prefixed to `ToolUseBlock` or `ToolResultBlock`. The deliberate choice was made *not* to rename `ToolResultContentItem`, `ToolResultSearchItem`, or `ToolResultLocalResource` to match their `type` field values, because (a) `text` would clash with `TextBlock`, and (b) the `type` values in that union are not obviously a closed set acting as discriminators in the same way as tool names.

No standalone diagnostic script. Full enforcement would require cross-referencing each subtype's definition name prefix against its `name` discriminator const (e.g. `BashToolUseBlock` → prefix `Bash` → tool name `bash`), which depends on schema structure and an empirically-determined tool name set. `naming.upper_camel_case` catches capitalisation violations. `naming.title_matches_key` is not relevant here — it checks `title == key`, which is a formatting rule and provides no coverage for the suffix pattern. The correct suffix (`ToolUseBlock` vs `ToolResultBlock`) and non-empty prefix can be verified manually with:

```python
import json
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
for name in schema['definitions']:
    if name.endswith('ToolUseBlock') and name != 'ToolUseBlock':
        if not name[:-len('ToolUseBlock')]:
            print(f'{name}: empty tool name prefix')
    if name.endswith('ToolResultBlock') and name not in ('ToolResultBlock', 'ToolResultBlockBase'):
        if not name[:-len('ToolResultBlock')]:
            print(f'{name}: empty tool name prefix')
```

---

## Structure

### `structure.field_order` · *enforced*

**Every definition begins with `title`, `description`, `type` (in that order).**

Consistent field ordering makes schemas easier to scan. `title` and `description` come first as the human-readable contract; `type` follows as the primary structural constraint. The only exception is the root schema, which begins with `$schema`.

```text
Diagnostic: src/test/diagnostics/structure.field_order.py
Repair:     src/test/repairs/structure.field_order.py
```

---

### `structure.bfs_order` · *enforced*

**Definitions are ordered in breadth-first referential encounter order.**

Reading the definitions top-to-bottom should follow the same order as reading the schema by following `$ref`s. This makes the file navigable as a solitary wave — unfolding and refolding a single schema at a time. Definitions unreachable via `$ref` (e.g. `ToolInput*` variants referenced only in descriptions) appear at the end in their original order. BFS order must be reapplied after any edit that adds or reorders definitions.

```text
Diagnostic: src/test/diagnostics/structure.bfs_order.py
Repair:     src/test/repairs/structure.bfs_order.py
```

---

### `structure.definitions_at_bottom` · *enforced*

**The `definitions` key is the last key in the root schema.**

The root schema header (`$schema`, `title`, `description`, `type`, `minItems`, `items`) is read first; `definitions` is a reference section consulted on demand.

```text
Diagnostic: src/test/diagnostics/structure.definitions_at_bottom.py
Repair:     src/test/repairs/structure.definitions_at_bottom.py
```

---

### `structure.required_subset_of_properties` · *enforced*

**Every `required` field is listed in `properties`.**

A required field not present in `properties` is a schema error — the validator will require a field it cannot validate.

```text
Diagnostic: src/test/diagnostics/structure.required_subset_of_properties.py
```

---

### `structure.no_redundant_additional_properties_true` · *enforced*

**No explicit `additionalProperties: true`.**

`additionalProperties: true` is the default in draft-4. Explicit occurrences are redundant noise. The meaningful values are `false` (closed schema) and absent (open schema).

```text
Diagnostic: src/test/diagnostics/structure.no_redundant_additional_properties_true.py
Repair:     src/test/repairs/structure.no_redundant_additional_properties_true.py
```

---

### `structure.all_definitions_reachable` · *enforced*

**Every definition is reachable from the root via `$ref`.**

Unreachable definitions are dead code. Known exceptions: `ToolInputComputerUse`, `ToolInputTextEditor`, `ToolInputCodeExecution` — documented stubs for API tools not yet observed in any export.

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

**Arrays that are never empty in observed exports have `minItems: 1`.**

Verified for the root array, `chat_messages`, and `content` (per message). Arrays that are sometimes empty (`attachments`, `files`, `citations`) intentionally have no `minItems`.

```text
Diagnostic: src/test/diagnostics/structure.minItems_on_non_empty_arrays.py
```

---

### `structure.pattern_constraints_enforced` · *enforced*

**String fields with known formats use `pattern` rather than documenting the regex only in `description`.**

Draft-4 `"pattern"` is enforced by `jsonschema.Draft4Validator`. Regex patterns that were previously documentation-only (in `description`) should be promoted to `"pattern"` so they are validated. This applies to `UuidV4`, `UuidV7`, `Timestamp`, `ToolId`, and any timestamp fields in other schemas. The `description` may retain a human-readable summary of the pattern but the regex itself belongs in `"pattern"`.

Known patterns:

- `UuidV4`: `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`
- `UuidV7`: `^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$`
- `Timestamp` (Z suffix, conversations.json): `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$`
- `TimestampOffset` (+00:00 suffix, projects.json): `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+00:00$`
- `ToolId`: `^toolu_[A-Za-z0-9]+$`

```text
Diagnostic: src/test/diagnostics/structure.pattern_constraints_enforced.py
```

```python
# inline illustration
import json, re
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
REGEX_RE = re.compile(r'Regex:|^\^.*\$$', re.MULTILINE)
def check(obj, path=''):
    if isinstance(obj, dict):
        if obj.get('type') == 'string':
            d = obj.get('description', '') or ''
            if REGEX_RE.search(d) and 'pattern' not in obj:
                print(f'{path}: has regex in description but no pattern constraint')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)
```

---

### `structure.property_order_matches_data` · *enforced*

**Properties within each schema appear in the same order as fields in the actual JSON data.**

Field order in JSON objects is not semantically significant, but consistent ordering between schema and data makes schemas easier to cross-reference. Field order is perfectly uniform across all instances of every object type in observed exports (sole exception: `PromptContextMetadataSearch`, where the optional `age` field is appended when present).

```text
Diagnostic: src/test/diagnostics/structure.property_order_matches_data.py
```

```python
# inline illustration (run against export data to re-derive canonical order)
import json
from collections import Counter, defaultdict
with open('conversations.json') as f:
    data = json.load(f)
orders = defaultdict(Counter)
for conv in data:
    orders['Conversation'][tuple(conv.keys())] += 1
    for msg in conv.get('chat_messages', []):
        orders['Message'][tuple(msg.keys())] += 1
        for block in msg.get('content', []):
            t = block.get('type')
            orders[f'ContentBlock({t})'][tuple(block.keys())] += 1
for name, counter in sorted(orders.items()):
    if len(counter) > 1:
        print(f'{name}: {len(counter)} distinct field orderings')
```

---

## Documentation

### `documentation.every_definition_has_title_and_description` · *enforced*

**Every definition has both `title` and `description`.**

Titles and descriptions surface as tooltips in VS Code when the schema is used as a documenter wrapper, making the schema self-documenting at the point of data inspection.

```text
Diagnostic: src/test/diagnostics/documentation.every_definition_has_title_and_description.py
Repair:     src/test/repairs/documentation.every_definition_has_title_and_description.py
```

---


### `documentation.api_links` · *advisory*

**Definitions with API counterparts have a `See:` link.**

Where a schema corresponds to a public Anthropic API concept, the description should include a `See: URL` pointing to the relevant documentation page.

```python
# diagnostic
import json
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    d = defn.get('description', '')
    if ('API' in d or 'Corresponds to' in d) and 'See:' not in d:
        print(f'{name}: mentions API but has no See: link')
```

---

### `documentation.null_only_fields_documented` · *enforced*

**Fields typed as `null` note this empirical observation in their description.**

A field typed as `null` is a strong empirical claim based on observed exports only. Checked on named definitions and named properties; anonymous `oneOf` branches (`{"type": "null"}`) are exempt.

```text
Diagnostic: src/test/diagnostics/documentation.null_only_fields_documented.py
```

```python
# repair: add standard null description to properties missing one
import json
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
defs = schema['definitions']
def fix(obj):
    if isinstance(obj, dict):
        if 'properties' in obj:
            for k, v in obj['properties'].items():
                if isinstance(v, dict) and v.get('type') == 'null' and 'description' not in v:
                    v['description'] = 'Always null in observed exports. Possibly reserved for future use.'
                    print(f'Fixed: {k}')
        for val in obj.values(): fix(val)
    elif isinstance(obj, list):
        for v in obj: fix(v)
fix({'definitions': defs})
with open('rsc/schema/chat-exports/conversations/v{N}.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `documentation.open_set_enums_documented` · *enforced*

**Enums that are likely open sets say so in their description.**

The caveat may appear on the definition itself or on the enum property. Exempt: single-value discriminators, and known closed sets (`sender: human/assistant`, `ContentBlock.type`). The check propagates the definition-level caveat to all nested enums.

```text
Diagnostic: src/test/diagnostics/documentation.open_set_enums_documented.py
```

```python
# repair: add open-set caveat to a specific enum property
import json
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
items = schema['definitions']['ToolInputRecommendClaudeApps']['properties']['app_ids']['items']
items['description'] = 'Observed values listed. Likely an open set — do not treat as exhaustive.'
with open('rsc/schema/chat-exports/conversations/v{N}.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `documentation.discriminator_fields_annotated` · *enforced*

**Discriminator fields are annotated with `description: "(discriminator)"`.**

Only checked on `type` and `name` properties of schemas referenced directly from a `oneOf`. Other single-value enums (e.g. `command: ['view']` in `ToolInputMemoryUserEdits`) are constraints, not discriminators, and are exempt.

```text
Diagnostic: src/test/diagnostics/documentation.discriminator_fields_annotated.py
```

---

### `documentation.inlined_property_descriptions` · *advisory*

**Individual properties with non-obvious semantics carry their own `description`.**

Not every property needs a description. But properties with surprising behaviour, empirical caveats, or cross-field relationships should have inline descriptions. Examples: `Conversation.summary` (may be empty string), `Message.updated_at` (always equals `created_at`), `Citation.start_index` (character offset).

```python
# diagnostic: list all properties that have no description (for human review)
import json
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'properties' in obj:
            for k, v in obj['properties'].items():
                if isinstance(v, dict) and '$ref' not in v and 'description' not in v:
                    print(f'{path}/{k}: no description')
        for k, v in obj.items():
            check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check(v, f'{path}[{i}]')
check({'definitions': schema['definitions']})
```

---

### `documentation.documenter_wrapper_pattern` · *informational*

**The `documenter.schema.json` pattern enables VS Code tooltips on data files.**

A self-referential wrapper file provides schema-aware editing and tooltip documentation on any JSON data file without embedding a `$schema` pointer in the data file itself. The `document` field references the actual schema, so when the `null` placeholder is replaced with a real data export, VS Code validates and documents it using `rsc/schema/chat-exports/conversations/v{N}.json`. Every `description` field in the schema surfaces as a tooltip at the corresponding location in the data.

```json
{
  "$schema": "rsc/schema/documenter.json",
  "title": "...",
  "description": "...",
  "properties": {
    "document": { "$ref": "./conversations/v{N}.json" }
  },
  "document": null
}
```

---

## Empirical Grounding

### `empirical.validate_against_all_known_exports` · *enforced*

**The schema must validate against all known exports.**

Every known export is a ground-truth test case. A failing export is always a schema bug, not a data bug. New exports should be validated immediately and any failures investigated before the export is considered incorporated. Validation is run by `src/main/chat-exports/validate.sh` and results written to `gen/<export>/validation/conversations/v{N}.log`. The pre-commit hook checks all `EXPECTED_PASS` (export, version) pairs and confirms each log contains `Valid!`.

```bash
src/main/chat-exports/RUNME.sh --chat-exports ../chat-exports
```

```python
# repair: iterate all errors to identify what needs fixing
import json
from jsonschema import Draft4Validator
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
with open('conversations.json') as f:
    data = json.load(f)
for error in Draft4Validator(schema).iter_errors(data):
    print(f'Path: {list(error.absolute_path)}')
    print(f'  {error.message}')
    print()
```

---

### `empirical.oneOf_branches_evidenced` · *enforced*

**Every branch of every `oneOf` is evidenced in at least one known export.**

An unevidenced `oneOf` branch should be documented as `"Not observed in this export"` rather than silently included.

```text
Diagnostic: src/test/diagnostics/empirical.oneOf_branches_evidenced.py
```

```python
# inline illustration: collect observed types and tool names from export data
import json
from collections import Counter
with open('conversations.json') as f:
    data = json.load(f)
block_types, tool_names, display_types = Counter(), Counter(), Counter()
for conv in data:
    for msg in conv.get('chat_messages', []):
        for block in msg.get('content', []):
            block_types[block.get('type')] += 1
            if block.get('type') in ('tool_use', 'tool_result'):
                tool_names[block.get('name')] += 1
            dc = block.get('display_content')
            if isinstance(dc, dict):
                display_types[dc.get('type')] += 1
print('Block types:', dict(block_types))
print('Tool names:', dict(tool_names))
print('Display content types:', dict(display_types))
```

---

### `empirical.tool_result_id_referential_integrity` · *manual*

**Every `tool_use_id` in a `ToolResultBlock` matches the `id` of a `ToolUseBlock` in the same `content` array.**

This cross-field constraint cannot be expressed in JSON Schema draft-4. Verified empirically: zero violations across all known exports.

**Checksum:** the original export returns `945`.

```jq
jq '[.[].chat_messages[].content |
  (map(select(.type=="tool_use")) | map(.id) | unique) as $ids |
  map(select(.type=="tool_result") | .tool_use_id) |
  map(. as $t | $ids | index($t) // error("unmatched tool_use_id: "+$t))] | length' \
  conversations.json
```

---

### `empirical.nullable_fields_surveyed` · *enforced*

**All `oneOf: [null, ...]` fields have been verified against observed data.**

Fields observed as always-null are typed as plain `"type": "null"`. Fields that are sometimes null retain `oneOf`. Anonymous `oneOf` branches are exempt from this check.

```text
Diagnostic: src/test/diagnostics/empirical.nullable_fields_surveyed.py
```

```python
# inline illustration: list all null-typed fields for human review
import json
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
defs = schema['definitions']
null_typed = []
for name, defn in defs.items():
    if defn.get('type') == 'null':
        null_typed.append(f'definition: {name}')
def find_null_props(obj, path=''):
    if isinstance(obj, dict):
        if 'properties' in obj:
            for k, v in obj['properties'].items():
                if isinstance(v, dict) and v.get('type') == 'null':
                    null_typed.append(f'property: {path}/{k}')
        for k, v in obj.items():
            if k != 'oneOf': find_null_props(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for v in obj: find_null_props(v, path)
find_null_props({'definitions': defs})
for f in null_typed: print(f'  {f}')
```

```python
# repair: verify a specific field's nullness against export data
import json
from collections import defaultdict
with open('conversations.json') as f:
    data = json.load(f)
field = 'flags'
counts = defaultdict(int)
for conv in data:
    for msg in conv.get('chat_messages', []):
        for block in msg.get('content', []):
            if field in block:
                v = block[field]
                counts['null' if v is None else type(v).__name__] += 1
print(f'{field}: {dict(counts)}')
```

---

### `empirical.uuid_format_consistency` · *advisory*

**UUIDs follow their declared format (v4 or v7) at each usage site.**

```python
# diagnostic
import json, re
with open('conversations.json') as f:
    data = json.load(f)
v4 = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
v7 = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$')
for ci, conv in enumerate(data):
    if not v4.match(conv['uuid']):
        print(f'conv[{ci}].uuid not v4: {conv["uuid"]}')
    for mi, msg in enumerate(conv.get('chat_messages', [])):
        if not v7.match(msg['uuid']):
            print(f'conv[{ci}].msg[{mi}].uuid not v7: {msg["uuid"]}')
```

---

### `empirical.field_order_uniform_in_data` · *informational*

**Field order within each object type is perfectly uniform across all instances in observed exports.**

The sole exception is `PromptContextMetadataSearch`, where the optional `age` field is appended only when present.

```jq
jq '[.[].chat_messages[].content[] | {type, keys: keys}] | group_by(.type) |
    map({type: .[0].type,
         distinct_key_orders: (map(.keys) | unique | length)})' \
    conversations.json
```

---

### `empirical.model_candidate_generator` · *informational*

**A candidate `model.json` can be generated from any schema by collecting `$ref` targets and their occurrence paths.**

The `gen_model_candidate.py` script traverses a schema, collects every `$ref` to a named definition, records the path at which it occurs, and retrieves the description from the definition itself (not the usage site — draft-4 `$ref` objects are opaque; sibling properties are ignored by validators). The root schema is included using its `title` as the entry name. A null description in the output is a canary for a missing or non-string description in the schema, which `documentation.every_definition_has_title_and_description` would also catch.

Run as: `python src/test/gen_model_candidate.py conversations` (stem only, no extension), from the repo root.

See `src/test/gen_model_candidate.py` for the full implementation.

---

## Composition Patterns

### `composition.discriminated_union_pattern` · *manual*

**Discriminated unions follow the wrapper / base / subtype pattern.**

A discriminated union is expressed as three layers:

1. A **wrapper** schema with exactly five fields: `title`, `description`, `type`, `allOf` (base ref + `Has*DiscriminatorProperty` ref), `oneOf` (subtype refs).
2. A **`...Base`** schema with `additionalProperties: false` and all shared fields, where the discriminator field is present but its value is unconstrained.
3. **n subtype** schemas, each specifying only the discriminator field (constrained to a single `enum` value) and any per-subtype fields.

Key insight: `allOf` and `oneOf` sit at the **wrapper** level, not inside the subtypes, which avoids `additionalProperties` conflicts. The `Has*DiscriminatorProperty` schema asserts the discriminator field is `required` and typed as a string.

Key-presence and primitive-type unions are not flagged — no diagnostic enforces this rule;
structural judgement at review time is sufficient.

---

### `composition.discriminator_values_disjoint` · *enforced*

**Discriminator enum values across all branches of a `oneOf` are mutually disjoint.**

```text
Diagnostic: src/test/diagnostics/composition.discriminator_values_disjoint.py
```

---

### `composition.base_schemas_closed` · *enforced*

**All `...Base` schemas have `additionalProperties: false`.**

The `...Base` schema is the definitive closed contract for all shared fields. Future changes to the export format are caught immediately.

```text
Diagnostic: src/test/diagnostics/composition.base_schemas_closed.py
```

---

### `composition.wrapper_has_five_fields` · *enforced*

**Union wrapper schemas have exactly five fields: `title`, `description`, `type`, `allOf`, `oneOf`.**

The wrapper is a pure structural combinator with no additional constraints.

```text
Diagnostic: src/test/diagnostics/composition.wrapper_has_five_fields.py
```

```python
# repair: remove unexpected fields from a wrapper (manual review recommended first)
import json
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
expected = {'title', 'description', 'type', 'allOf', 'oneOf'}
for name, defn in schema['definitions'].items():
    if 'oneOf' in defn and 'allOf' in defn:
        for k in set(defn.keys()) - expected:
            print(f'{name}: removing extra field "{k}" = {defn[k]!r}')
            del defn[k]
with open('rsc/schema/chat-exports/conversations/v{N}.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `composition.no_additional_properties_on_subtypes` · *enforced*

**Subtype schemas must not combine `additionalProperties: false` with `allOf` referencing a schema that has `properties`.**

This would cause the base's properties to be rejected as "additional". The constraint belongs exclusively on the `...Base` schema. This was the key insight from the proof-of-concept.

```text
Diagnostic: src/test/diagnostics/composition.no_additional_properties_on_subtypes.py
```

```python
# repair: remove additionalProperties: false from the conflicting subtype
import json
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
defs = schema['definitions']
for name, defn in defs.items():
    if defn.get('additionalProperties') is False and 'allOf' in defn:
        for ref_obj in defn.get('allOf', []):
            ref = ref_obj.get('$ref', '')[len('#/definitions/'):]
            if ref and defs.get(ref, {}).get('properties'):
                del defn['additionalProperties']
                print(f'Fixed: {name}')
with open('rsc/schema/chat-exports/conversations/v{N}.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `composition.base_not_used_directly` · *enforced*

**`...Base` schemas are never referenced directly from `oneOf` lists.**

The base is an implementation detail of the wrapper. Direct `oneOf` references would bypass the discriminated union pattern.

```text
Diagnostic: src/test/diagnostics/composition.base_not_used_directly.py
```

---

### `composition.use_refs_not_inline` · *advisory*

**Repeated schemas are factored into definitions and referenced via `$ref`.**

Any schema appearing more than once should be a named definition. Applied to `NullableString`, `NullableBoolean`, `Timestamp`, `Flags`, `DisplayContent`, `IntegrationName`, `IconName`, etc.

```python
# diagnostic: find identical inline schema objects appearing more than once
import json
from collections import Counter
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
counts = Counter()
def walk(obj):
    if isinstance(obj, dict) and '$ref' not in obj and 'definitions' not in obj:
        key = json.dumps(obj, sort_keys=True)
        if len(key) > 20: counts[key] += 1
        for v in obj.values(): walk(v)
    elif isinstance(obj, list):
        for v in obj: walk(v)
walk(schema)
for k, c in counts.items():
    if c > 1: print(f'Appears {c}x: {k[:80]}')
```

---

## API Correspondence

### `api.export_is_api_plus_envelope` · *informational*

**The export format is the Claude API data model plus a persistence/UI envelope.**

The core `ContentBlock` discriminated union (`text`, `tool_use`, `tool_result`) is shared verbatim with the API. Envelope fields (`start_timestamp`, `stop_timestamp`, `display_content`, `integration_*`, `icon_name`, `approval_*`, `is_mcp_app`, `mcp_server_url`) are claude.ai additions. New fields in exports are likely either new API fields or new UI envelope fields.

See: <https://platform.claude.com/docs/en/build-with-claude/working-with-messages>

---

### `api.sender_vs_role` · *informational*

**Export uses `sender: human/assistant`; API uses `role: user/assistant`.**

```jq
jq '[.[].chat_messages[].sender] | unique' conversations.json
```

---

### `api.tool_names_internal_vs_public` · *informational*

**Some tool names are claude.ai-internal with no public API documentation.**

`recent_chats`, `conversation_search`, and `recommend_claude_apps` are claude.ai-internal. New tool names should be investigated to determine whether they are public API tools (add `See:` link) or internal ones (note as such).

```python
# diagnostic: list all observed tool names
import json
from collections import Counter
with open('conversations.json') as f:
    data = json.load(f)
names = Counter()
for conv in data:
    for msg in conv.get('chat_messages', []):
        for block in msg.get('content', []):
            if block.get('type') in ('tool_use', 'tool_result'):
                names[block.get('name')] += 1
for name, count in sorted(names.items()):
    print(f'{count:4d}  {name}')
```

---

### `api.draft4_limitations` · *informational*

**Known draft-4 limitations and our workarounds.**

- **No `if`/`then`/`else`**: discriminated unions use the `allOf`/`oneOf` wrapper/base/subtype pattern instead.
- **`$ref` siblings are ignored**: move sibling documentation into the referenced definition's `description`.
- **No `nullable` shorthand**: use `oneOf: [{type: null}, ...]` or a named `NullableString` definition.
- **No `$comment`**: use `description` for all documentation including internal notes.
- **No cross-field constraints**: document in `description` with a verification snippet.
- **No `format` enforcement**: `format: date-time` is advisory only; use `pattern` instead.

---

## Integrity Constraints

### `integrity.tool_use_result_pairing` · *advisory*

**Every `tool_use` block has a corresponding `tool_result` block in the same `content` array.**

```python
# diagnostic
import json
with open('conversations.json') as f:
    data = json.load(f)
for ci, conv in enumerate(data):
    for mi, msg in enumerate(conv.get('chat_messages', [])):
        content = msg.get('content', [])
        use_ids = {b['id'] for b in content if b.get('type') == 'tool_use'}
        result_ids = {b['tool_use_id'] for b in content if b.get('type') == 'tool_result'}
        unpaired = use_ids - result_ids
        if unpaired:
            print(f'conv[{ci}].msg[{mi}]: unpaired tool_use ids: {unpaired}')
```

---

### `integrity.message_order` · *advisory*

**Messages within a conversation are ordered by `created_at`.**

```python
# diagnostic
import json
with open('conversations.json') as f:
    data = json.load(f)
for ci, conv in enumerate(data):
    msgs = conv.get('chat_messages', [])
    for i in range(1, len(msgs)):
        if msgs[i]['created_at'] < msgs[i-1]['created_at']:
            print(f'conv[{ci}]: message {i} created_at out of order')
```

---

## Open Questions

This section collects things we want to think about but don't yet have firm ideas, feasibility assessments, or decisions on.

---

### `open.semantic_undecidability` · *open*

**Some schema correctness questions are semantically undecidable by automated tools alone.**

The `Has*DiscriminatorProperty` pattern is a good example: whether it has been applied "correctly" and "completely" depends on a semantic understanding of what constitutes a union wrapper. An automated tool can check that every structural `oneOf` has a `Has*DiscriminatorProperty` in its `allOf` — but it cannot determine whether a given `oneOf` *should* have one (e.g. `PromptContextMetadata` discriminates on key presence, not a type field).

**Question:** Is there a principled way to classify `oneOf` unions by their discrimination strategy (type-field, name-field, key-presence, structural) and apply different checks to each class?

---

### `open.draft7_migration` · *open*

**Should the schema be migrated to JSON Schema draft-7 or later?**

Draft-7 would enable `if`/`then`/`else` (cleaner discriminated unions), `$comment` (internal notes separate from user-facing descriptions), and `type: [string, null]` (cleaner nullable). The cost is potential loss of VS Code tooltip support.

**Questions:** Does VS Code's JSON language server support draft-7 for tooltip purposes? Would `if`/`then`/`else` actually simplify the schema significantly? Is the wrapper/base/subtype pattern still needed in draft-7?

---

### `open.toolinput_schemas_in_oneof` · *open*

**Can `ToolInput*` schemas be incorporated into the `oneOf` discriminated union?**

Currently `ToolInput*` schemas are documented but not enforced via `oneOf` because they overlap structurally. In draft-4, one approach is to fold the `input` schema directly into each `ToolUseBlock` subtype. In draft-7, `if`/`then`/`else` keyed on `name` would handle this cleanly.

**Question:** Is it worth restructuring the subtypes to inline their `input` schemas, even at the cost of losing standalone `ToolInput*` definitions?

---

### `open.attachment_file_type_convention` · *open*

**The `file_type` field in `Attachment` uses an inconsistent naming convention.**

Observed values include `txt` (extension-style) and `text/html` (MIME-type-style). It is unclear whether this is a server-side inconsistency or intentional.

**Question:** Is the mixed convention stable? Should the schema enumerate known values more precisely?

---

### `open.display_content_vs_api` · *open*

**The `display_content` field is a claude.ai UI addition, but its structure closely mirrors API content block types.**

It is unclear whether `display_content` is a rendering hint derived from the tool result content, or independently specified.

**Question:** Is `display_content` derived or independent?

---

### `open.mcp_server_url_semantics` · *open*

**`mcp_server_url` is always null in observed exports.**

When non-null, it presumably identifies a remote MCP server. It is unclear whether a non-null value changes anything else in the block structure.

**Question:** When `mcp_server_url` is non-null, do `integration_name`, `icon_name`, `is_mcp_app` change? Should these be co-constrained?

---

### `open.principles_document_schema` · *open*

**Should this principles document itself have a JSON Schema?**

The current markdown-with-frontmatter approach is human-friendly but requires parsing heuristics for machine consumption.

**Question:** What is the right format? A structured JSON or YAML document with embedded markdown strings would be more machine-friendly but less pleasant to edit. Is there a hybrid approach?

---

## Maintenance Workflow

### `maintenance.new_export_workflow` · *manual*

**Workflow for incorporating a new export.**

See `rsc/schema/chat-exports/conversations/workflow.md` for the full loop. Summary:

1. Validate new export against all schemas.
2. Run `src/test/pre_commit.py` to check all diagnostics.
3. Categorise failures by root cause; refine diagnostics before fixing schema.
4. Fix genuine schema issues using repair scripts in `src/test/repairs/`.
5. Re-run `src/test/pre_commit.py` until all checks pass.
6. Update this document and `rsc/schema/chat-exports/conversations/workflow.md` as needed.
7. Commit.

---

### `maintenance.compress_before_upload` · *informational*

**Use a redacted/compressed export for schema development.**

The full export contains personal conversation content. A compressed version is sufficient for schema development and safe to share.

```jq
# Step 1: redact string values
jq 'walk(if type == "object" and has("text") and .text != ""
         and (.text | type) == "string"
         then .text = "[text]" else . end)' \
   conversations.json > compressed.json

# Step 2: optionally reduce arrays to first element for skeleton inspection
jq 'walk(if type == "array" and length > 1 then [.[0]] else . end)' \
   compressed.json > skeleton.json
```

---

### `maintenance.bfs_reorder_after_edits` · *enforced*

**Reapply BFS ordering after any structural edits.**

```text
Diagnostic: src/test/diagnostics/structure.bfs_order.py
Repair:     src/test/repairs/structure.bfs_order.py
```

Run as: `python src/test/repairs/structure.bfs_order.py rsc/schema/chat-exports/conversations/v{N}.json`

---

### `maintenance.verify_before_commit` · *manual*

**No change is committed until it has been tested and the result verified.**

For schema changes: validation outputs must be current and passing. For script changes: the script must have been run against real data and its output inspected. For documentation changes: the document must have been read through after the last edit.

The pre-commit hook enforces what it can mechanically, but it cannot substitute for human verification that a change does what it claims.

---

*This document was developed iteratively alongside `rsc/schema/chat-exports/conversations/v{N}.json` over multiple sessions. The schema was reverse-engineered from Claude.ai bulk data exports; all constraints are empirically grounded unless explicitly noted otherwise. The Open Questions section is intentionally incomplete — it should grow as new questions arise and shrink as decisions are made.*
