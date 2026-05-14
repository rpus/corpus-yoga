---
schema_file: rsc/schema/chat-exports/conversations/v6.json
principles_file: rsc/schema/chat-exports/conversations/principles.md
workflow_file: rsc/schema/chat-exports/conversations/workflow.md
version: "1.3"
---

# Schema Design Principles for `rsc/schema/chat-exports/conversations/v{N}.json`

The generic schema design principles in [`rsc/schema/principles.md`](../../principles.md) apply
to this schema in full. Read that document first. This document records only the
conversations-specific empirical content, API correspondence, integrity constraints,
open questions, and maintenance notes.

---

## Conversations-Specific Naming

### `naming.subtype_naming_convention` · *advisory*

**Tool block subtypes are named `{ToolName}ToolUseBlock` / `{ToolName}ToolResultBlock`.**

The tool name is converted from snake\_case to UpperCamelCase and prefixed to `ToolUseBlock`
or `ToolResultBlock`. Not renamed: `ToolResultContentItem`, `ToolResultSearchItem`,
`ToolResultLocalResource` — (a) `text` would clash with `TextBlock`, and (b) the `type`
values in that union are not a closed discriminator set in the same way as tool names.

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

## Conversations-Specific Structure

Known pattern constraints:

- `UuidV4`: `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`
- `UuidV7`: `^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$`
- `Timestamp` (Z suffix, conversations.json): `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$`
- `TimestampOffset` (+00:00 suffix, projects.json): `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+00:00$`
- `ToolId`: `^toolu_[A-Za-z0-9]+$`

Known unreachable stubs: `ToolInputComputerUse`, `ToolInputTextEditor`,
`ToolInputCodeExecution` — documented for API tools not yet observed in any export.

`PromptContextMetadataSearch` is the sole exception to uniform field order: the optional
`age` field is appended only when present.

---

## Conversations-Specific Documentation

### `documentation.api_links` · *advisory*

**Definitions with API counterparts have a `See:` link.**

```python
import json
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    d = defn.get('description', '')
    if ('API' in d or 'Corresponds to' in d) and 'See:' not in d:
        print(f'{name}: mentions API but has no See: link')
```

---

### `documentation.documenter_wrapper_pattern` · *informational*

**The `documenter.schema.json` pattern enables VS Code tooltips on data files.**

```json
{
  "$schema": "rsc/schema/documenter.json",
  "title": "...",
  "description": "...",
  "properties": { "document": { "$ref": "./conversations/v{N}.json" } },
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

Run as: `python src/main/model/gen_model_candidate.py conversations` (stem only, no extension), from the repo root.

See `src/main/model/gen_model_candidate.py` for the full implementation.

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

*This document was developed iteratively alongside `rsc/schema/chat-exports/conversations/v{N}.json` over multiple sessions. The schema was reverse-engineered from Claude.ai bulk data exports; all constraints are empirically grounded unless explicitly noted otherwise. The Open Questions section is intentionally incomplete — it should grow as new questions arise and shrink as decisions are made.*
