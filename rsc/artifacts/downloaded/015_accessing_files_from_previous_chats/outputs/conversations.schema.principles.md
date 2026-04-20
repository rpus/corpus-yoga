---
title: Schema Design Principles for conversations.schema.json
schema_file: conversations.schema.json
draft: "http://json-schema.org/draft-04/schema#"
version: "1.1"
---

# Schema Design Principles for `conversations.schema.json`

A living document of design principles, diagnostics, and repairs for `conversations.schema.json`. Each principle has a machine-runnable diagnostic (Python or jq) and a sample repair snippet. This document should be kept updated in parallel with the schema and its validation runs.

Principles are organised into eight categories: [Naming](#naming), [Structure](#structure), [Documentation](#documentation), [Empirical Grounding](#empirical-grounding), [Composition Patterns](#composition-patterns), [API Correspondence](#api-correspondence), [Integrity Constraints](#integrity-constraints), and [Open Questions](#open-questions). A final [Maintenance Workflow](#maintenance-workflow) section collects operational procedures.

Each principle has a **status**:
- `enforced` — a diagnostic exists and should always pass
- `advisory` — worth checking; violations may be intentional
- `manual` — requires human judgement; no fully automatable check
- `informational` — context only; no check
- `open` — genuinely undecided; no principle yet established; here for awareness and future discussion

---

## Naming

### `naming.upper_camel_case` · *enforced*

**All definition names are UpperCamelCase.**

Consistent UpperCamelCase for definition names cleanly distinguishes schema type names from data field names (which are snake_case or camelCase). This means a `$ref` is always visually distinct from a property key — e.g. `"uuid": {"$ref": "#/definitions/UuidV4"}` is unambiguous at a glance.

```python
# diagnostic
import json, re
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name in schema['definitions']:
    if not re.match(r'^[A-Z][A-Za-z0-9]*$', name):
        print(f'Not UpperCamelCase: {name}')
```

```python
# repair: rename a definition and update all $refs
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
OLD, NEW = 'badName', 'BadName'
text = json.dumps(schema, indent=2)
text = text.replace(f'"#/definitions/{OLD}"', f'"#/definitions/{NEW}"')
schema = json.loads(text)
schema['definitions'][NEW] = schema['definitions'].pop(OLD)
schema['definitions'][NEW]['title'] = NEW
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `naming.title_matches_key` · *enforced*

**Every definition's `title` matches its key.**

The `title` field is the human-readable name of the schema. It should match the definition key exactly so that tooling (e.g. VS Code tooltips) shows the correct name.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    if defn.get('title') != name:
        print(f'title mismatch: key={name!r}, title={defn.get("title")!r}')
```

```python
# repair: set title to match key for all mismatches
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    if defn.get('title') != name:
        defn['title'] = name
        print(f'Fixed: {name}')
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `naming.property_keys_lowercase` · *enforced*

**All property keys in data schemas are lowercase or snake\_case.**

Property keys mirror the actual JSON data fields, which follow snake\_case. UpperCamelCase keys would indicate a wrongly-renamed property — a bug encountered during the `timestamp`/`flags`/`display_content` renaming, where the rename script accidentally capitalised property keys as well as definition keys.

```python
# diagnostic
import json, re
with open('conversations.schema.json') as f:
    schema = json.load(f)
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'properties' in obj:
            for k in obj['properties']:
                if re.match(r'^[A-Z]', k):
                    print(f'{path}: uppercase property key "{k}"')
        for k, v in obj.items():
            check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check(v, f'{path}[{i}]')
check(schema)
```

```python
# repair: rename an uppercase property key to lowercase (example)
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
# Example: rename 'Flags' property key to 'flags' in TextBlock
for block in ['TextBlock', 'ToolUseBlock', 'ToolResultBlock']:
    props = defs[block]['properties']
    if 'Flags' in props:
        props['flags'] = props.pop('Flags')
        print(f'Fixed {block}')
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `naming.subtype_naming_convention` · *enforced*

**Tool block subtypes are named `{ToolName}ToolUseBlock` / `{ToolName}ToolResultBlock`.**

The tool name is converted from snake\_case to UpperCamelCase and prefixed to `ToolUseBlock` or `ToolResultBlock`. The deliberate choice was made *not* to rename `ToolResultContentItem`, `ToolResultSearchItem`, or `ToolResultLocalResource` to match their `type` field values, because (a) `text` would clash with `TextBlock`, and (b) the `type` values in that union are not obviously a closed set acting as discriminators in the same way as tool names.

```python
# diagnostic
import json, re
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
for name in defs:
    if name.endswith('ToolUseBlock') and name != 'ToolUseBlock':
        base = name[:-len('ToolUseBlock')]
        if not base:
            print(f'{name}: empty tool name prefix')
    if name.endswith('ToolResultBlock') and name not in ('ToolResultBlock', 'ToolResultBlockBase'):
        base = name[:-len('ToolResultBlock')]
        if not base:
            print(f'{name}: empty tool name prefix')
print('Subtype naming check complete')
```

```python
# repair: add a new tool subtype pair for a new tool name
import json
from collections import deque
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
TOOL_NAME = 'new_tool'         # snake_case tool name
TYPE_NAME = 'NewTool'          # UpperCamelCase prefix
INPUT_REF = 'ToolInputNewTool' # corresponding ToolInput* schema

for suffix, wrapper in [('ToolUseBlock', 'ToolUseBlock'), ('ToolResultBlock', 'ToolResultBlock')]:
    subtype_name = f'{TYPE_NAME}{suffix}'
    defs[subtype_name] = {
        'title': subtype_name,
        'description': f'Tool {"use" if "Use" in suffix else "result"} block for the {TOOL_NAME} tool.',
        'type': 'object',
        'required': ['name', 'input'] if 'Use' in suffix else ['name'],
        'properties': {
            'name': {'description': '(discriminator)', 'enum': [TOOL_NAME]},
            **({'input': {'$ref': f'#/definitions/{INPUT_REF}'}} if 'Use' in suffix else {})
        }
    }
    wrapper_def = defs[wrapper]
    wrapper_def['oneOf'].append({'$ref': f'#/definitions/{subtype_name}'})

# Also add to ToolName enum
defs['ToolName']['enum'].append(TOOL_NAME)
defs['ToolName']['enum'].sort()

with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Added {TYPE_NAME}ToolUseBlock and {TYPE_NAME}ToolResultBlock')
```

---

## Structure

### `structure.field_order` · *enforced*

**Every definition begins with `title`, `description`, `type` (in that order).**

Consistent field ordering makes schemas easier to scan. `title` and `description` come first as the human-readable contract; `type` follows as the primary structural constraint. The only exception is the root schema, which begins with `$schema`.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    keys = list(defn.keys())
    if keys[0] != 'title':
        print(f'{name}: first field is "{keys[0]}", expected "title"')
    elif len(keys) < 2 or keys[1] != 'description':
        second = keys[1] if len(keys) > 1 else 'missing'
        print(f'{name}: second field is "{second}", expected "description"')
```

```python
# repair: reorder title/description to front of all definitions
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    ordered = {}
    for k in ['title', 'description']:
        if k in defn:
            ordered[k] = defn[k]
    for k, v in defn.items():
        if k not in ordered:
            ordered[k] = v
    schema['definitions'][name] = ordered
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `structure.bfs_order` · *enforced*

**Definitions are ordered in breadth-first referential encounter order.**

Reading the definitions top-to-bottom should follow the same order as reading the schema by following `$ref`s. This makes the file navigable as a solitary wave — unfolding and refolding a single schema at a time. Definitions unreachable via `$ref` (e.g. `ToolInput*` variants referenced only in descriptions) appear at the end in their original order. BFS order must be reapplied after any edit that adds or reorders definitions.

```python
# diagnostic
import json
from collections import deque
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
def find_refs_ordered(obj):
    refs, seen = [], set()
    def walk(o):
        if isinstance(o, dict):
            if '$ref' in o:
                r = o['$ref'][len('#/definitions/'):]
                if r not in seen:
                    seen.add(r); refs.append(r)
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(obj); return refs
order, visited, queue = [], set(), deque(['Conversation'])
while queue:
    node = queue.popleft()
    if node in visited: continue
    visited.add(node); order.append(node)
    for dep in find_refs_ordered(defs.get(node, {})):
        if dep not in visited and dep in defs: queue.append(dep)
for k in defs:
    if k not in visited: order.append(k)
for i, (cur, bfs) in enumerate(zip(list(defs.keys()), order)):
    if cur != bfs:
        print(f'Position {i+1}: current={cur}, expected={bfs}')
```

```python
# repair: reapply BFS ordering
import json
from collections import deque
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
def find_refs_ordered(obj):
    refs, seen = [], set()
    def walk(o):
        if isinstance(o, dict):
            if '$ref' in o:
                r = o['$ref'][len('#/definitions/'):]
                if r not in seen:
                    seen.add(r); refs.append(r)
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(obj); return refs
order, visited, queue = [], set(), deque(['Conversation'])
while queue:
    node = queue.popleft()
    if node in visited: continue
    visited.add(node); order.append(node)
    for dep in find_refs_ordered(defs.get(node, {})):
        if dep not in visited and dep in defs: queue.append(dep)
for k in defs:
    if k not in visited: order.append(k)
schema['definitions'] = {k: defs[k] for k in order}
defs_out = schema.pop('definitions')
schema['definitions'] = defs_out
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Reordered {len(order)} definitions')
```

---

### `structure.definitions_at_bottom` · *enforced*

**The `definitions` key is the last key in the root schema.**

The root schema header (`$schema`, `title`, `description`, `type`, `minItems`, `items`) is read first; `definitions` is a reference section consulted on demand.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
keys = list(schema.keys())
if keys[-1] != 'definitions':
    print(f'definitions is not last: position {keys.index("definitions")+1} of {len(keys)}')
```

```python
# repair: move definitions to bottom
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema.pop('definitions')
schema['definitions'] = defs
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `structure.required_subset_of_properties` · *enforced*

**Every `required` field is listed in `properties`.**

A required field not present in `properties` is a schema error — the validator will require a field it cannot validate.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'required' in obj and 'properties' in obj:
            props = set(obj['properties'].keys())
            for f in obj['required']:
                if f not in props:
                    print(f'{path}: required field "{f}" not in properties')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)
```

```python
# repair: add a missing property stub for each required field that lacks one
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
def fix(obj, path=''):
    if isinstance(obj, dict):
        if 'required' in obj and 'properties' in obj:
            for f in obj['required']:
                if f not in obj['properties']:
                    obj['properties'][f] = {}
                    print(f'{path}: added stub for required "{f}"')
        for k, v in obj.items(): fix(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): fix(v, f'{path}[{i}]')
fix(schema)
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `structure.no_redundant_additional_properties_true` · *enforced*

**No explicit `additionalProperties: true`.**

`additionalProperties: true` is the default in draft-4. Explicit occurrences are redundant noise.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
def check(obj, path=''):
    if isinstance(obj, dict):
        if obj.get('additionalProperties') is True:
            print(f'{path}: redundant additionalProperties: true')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)
```

```python
# repair: remove all explicit additionalProperties: true
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
count = 0
def fix(obj):
    global count
    if isinstance(obj, dict):
        if obj.get('additionalProperties') is True:
            del obj['additionalProperties']
            count += 1
        for v in obj.values(): fix(v)
    elif isinstance(obj, list):
        for v in obj: fix(v)
fix(schema)
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Removed {count} occurrences')
```

---

### `structure.all_definitions_reachable` · *enforced*

**Every definition is reachable from the root via `$ref`.**

Unreachable definitions are dead code. Known exceptions: `ToolInputComputerUse`, `ToolInputTextEditor`, `ToolInputCodeExecution` — documented stubs for API tools not yet observed in any export.

```python
# diagnostic
import json
from collections import deque
KNOWN_UNREACHABLE = {
    'ToolInputComputerUse', 'ToolInputTextEditor', 'ToolInputCodeExecution'
}
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
def find_refs(obj):
    refs = set()
    def walk(o):
        if isinstance(o, dict):
            if '$ref' in o: refs.add(o['$ref'][len('#/definitions/'):])
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(obj); return refs
visited, queue = set(), deque(['Conversation'])
while queue:
    node = queue.popleft()
    if node in visited: continue
    visited.add(node)
    for dep in find_refs(defs.get(node, {})):
        if dep in defs: queue.append(dep)
for k in defs:
    if k not in visited and k not in KNOWN_UNREACHABLE:
        print(f'Unexpected unreachable: {k}')
```

```python
# repair: remove a genuinely dead definition
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
DEAD = 'ObsoleteDefinition'
del schema['definitions'][DEAD]
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
print(f'Removed {DEAD}')
```

---

### `structure.no_dangling_refs` · *enforced*

**Every `$ref` target exists in `definitions`.**

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = set(schema['definitions'].keys())
def check(obj, path=''):
    if isinstance(obj, dict):
        if '$ref' in obj:
            t = obj['$ref']
            if t.startswith('#/definitions/'):
                name = t[len('#/definitions/'):]
                if name not in defs:
                    print(f'{path}: dangling $ref to "{name}"')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)
```

```python
# repair: find all dangling refs and list their target names for manual resolution
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = set(schema['definitions'].keys())
dangling = set()
def check(obj):
    if isinstance(obj, dict):
        if '$ref' in obj:
            t = obj['$ref']
            if t.startswith('#/definitions/'):
                name = t[len('#/definitions/'):]
                if name not in defs: dangling.add(name)
        for v in obj.values(): check(v)
    elif isinstance(obj, list):
        for v in obj: check(v)
check(schema)
print('Dangling refs to resolve:', sorted(dangling))
```

---

### `structure.minItems_on_non_empty_arrays` · *enforced*

**Arrays that are never empty in observed exports have `minItems: 1`.**

Verified for the root array, `chat_messages`, and `content` (per message). Arrays that are sometimes empty (`attachments`, `files`, `citations`) intentionally have no `minItems`.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
checks = [
    ('root array', schema),
    ('chat_messages', defs['Conversation']['properties']['chat_messages']),
    ('content', defs['Message']['properties']['content']),
]
for label, obj in checks:
    if obj.get('type') == 'array' and obj.get('minItems', 0) < 1:
        print(f'{label}: expected minItems: 1')
```

```python
# repair: add minItems: 1 to a specific array schema
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
# Example: fix root array
schema['minItems'] = 1
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `structure.property_order_matches_data` · *enforced*

**Properties within each schema appear in the same order as fields in the actual JSON data.**

Field order in JSON objects is not semantically significant, but consistent ordering between schema and data makes schemas easier to cross-reference. Field order is perfectly uniform across all instances of every object type in observed exports (sole exception: `PromptContextMetadataSearch`, where `age` is optional and appended when present).

```python
# diagnostic: check field order uniformity in data
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
        for order, count in counter.most_common():
            print(f'  {count}x: {list(order)}')
```

```python
# repair: reorder properties of a definition to match observed data order
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
DATA_ORDER = ['start_timestamp', 'stop_timestamp', 'flags', 'type', 'text', 'citations']
defn = schema['definitions']['TextBlock']
props = defn['properties']
defn['properties'] = {k: props[k] for k in DATA_ORDER if k in props}
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

## Documentation

### `documentation.every_definition_has_title_and_description` · *enforced*

**Every definition has both `title` and `description`.**

Titles and descriptions surface as tooltips in VS Code when the schema is used as a documenter wrapper, making the schema self-documenting at the point of data inspection.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    if 'title' not in defn:
        print(f'{name}: missing title')
    if 'description' not in defn:
        print(f'{name}: missing description')
```

```python
# repair: add placeholder title and description to definitions missing them
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    if 'title' not in defn:
        defn['title'] = name
        print(f'{name}: added title')
    if 'description' not in defn:
        defn['description'] = f'TODO: add description for {name}.'
        print(f'{name}: added placeholder description')
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `documentation.descriptions_end_with_full_stop` · *enforced*

**All descriptions end with a full stop (or other recognised terminal punctuation).**

Recognised terminals: `.` (sentence), `)` (discriminator annotation), `$` (regex), a URL, or `.json` (jq snippet filename).

```python
# diagnostic
import json, re
URL_RE = re.compile(r'https?://\S+$')
def valid_end(d):
    return (d.endswith('.') or d.endswith(')')
            or d.endswith('$') or bool(URL_RE.search(d))
            or d.endswith('.json'))
with open('conversations.schema.json') as f:
    schema = json.load(f)
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'description' in obj and isinstance(obj['description'], str):
            d = obj['description']
            if d and not valid_end(d):
                print(f'{path}: ...{d[-40:]!r}')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)
```

```python
# repair: append missing full stop to flagged descriptions
import json, re
URL_RE = re.compile(r'https?://\S+$')
def valid_end(d):
    return (d.endswith('.') or d.endswith(')')
            or d.endswith('$') or bool(URL_RE.search(d))
            or d.endswith('.json'))
with open('conversations.schema.json') as f:
    schema = json.load(f)
def fix(obj):
    if isinstance(obj, dict):
        if 'description' in obj and isinstance(obj['description'], str):
            d = obj['description']
            if d and not valid_end(d):
                obj['description'] = d + '.'
        for v in obj.values(): fix(v)
    elif isinstance(obj, list):
        for v in obj: fix(v)
fix(schema)
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `documentation.api_links` · *advisory*

**Definitions with API counterparts have a `See:` link.**

Where a schema corresponds to a public Anthropic API concept, the description should include a `See: URL` pointing to the relevant documentation page.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    d = defn.get('description', '')
    if ('API' in d or 'Corresponds to' in d) and 'See:' not in d:
        print(f'{name}: mentions API but has no See: link')
```

```python
# repair: append a See: link to a specific definition
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
NAME = 'TextBlock'
URL = 'https://platform.claude.com/docs/en/build-with-claude/citations'
d = schema['definitions'][NAME]['description']
if not d.endswith('.'):
    d += '.'
schema['definitions'][NAME]['description'] = d + f' See: {URL}'
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `documentation.null_only_fields_documented` · *enforced*

**Fields typed as `null` note this empirical observation in their description.**

A field typed as `null` is a strong empirical claim based on observed exports only. Checked on named definitions and named properties; anonymous `oneOf` branches (`{"type": "null"}`) are exempt.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
fails = []
for name, defn in defs.items():
    if defn.get('type') == 'null':
        d = defn.get('description', '')
        if 'null' not in d.lower() and 'observed' not in d.lower():
            fails.append(f'definition {name}')
def check_props(obj, path=''):
    if isinstance(obj, dict):
        if 'properties' in obj:
            for k, v in obj['properties'].items():
                if isinstance(v, dict) and v.get('type') == 'null':
                    d = v.get('description', '')
                    if 'null' not in d.lower() and 'observed' not in d.lower():
                        fails.append(f'{path}/properties/{k}')
        for k, v in obj.items():
            if k != 'oneOf': check_props(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check_props(v, f'{path}[{i}]')
check_props({'definitions': defs})
for f in fails: print(f)
```

```python
# repair: add standard description to null-typed properties lacking one
import json
with open('conversations.schema.json') as f:
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
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `documentation.open_set_enums_documented` · *enforced*

**Enums that are likely open sets say so in their description.**

The caveat may appear on the definition itself or on the enum property. Exempt: single-value discriminators, and known closed sets (`sender: human/assistant`, `ContentBlock.type`). The check propagates the definition-level caveat to all nested enums.

```python
# diagnostic
import json
KNOWN_CLOSED = {
    frozenset(['human', 'assistant']),
    frozenset(['text', 'tool_use', 'tool_result']),
}
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
fails = []
for defn_name, defn in defs.items():
    defn_desc = defn.get('description', '')
    defn_open = 'open set' in defn_desc or 'exhaustive' in defn_desc
    def check(obj, path=''):
        if isinstance(obj, dict):
            if 'enum' in obj and len(obj['enum']) > 1:
                vals = frozenset(obj['enum'])
                local_desc = obj.get('description', '')
                local_ok = ('open set' in local_desc or 'exhaustive' in local_desc
                            or 'discriminator' in local_desc)
                if vals not in KNOWN_CLOSED and not defn_open and not local_ok:
                    fails.append(f'{defn_name}{path}: {sorted(obj["enum"])}')
            for k, v in obj.items(): check(v, f'/{k}')
        elif isinstance(obj, list):
            for i, v in enumerate(obj): check(v, f'[{i}]')
    check(defn)
for f in fails: print(f)
```

```python
# repair: add open-set caveat to an enum property
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
# Example: fix an items enum inside a definition
items = schema['definitions']['ToolInputRecommendClaudeApps']['properties']['app_ids']['items']
items['description'] = (
    'Observed values listed. Likely an open set — do not treat as exhaustive.'
)
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `documentation.discriminator_fields_annotated` · *enforced*

**Discriminator fields are annotated with `description: "(discriminator)"`.**

Only checked on `type` and `name` properties of schemas referenced directly from a `oneOf`. Other single-value enums (e.g. `command: ['view']` in `ToolInputMemoryUserEdits`) are constraints, not discriminators, and are exempt.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
oneof_refs = set()
def collect(obj):
    if isinstance(obj, dict):
        if 'oneOf' in obj:
            for b in obj['oneOf']:
                if '$ref' in b: oneof_refs.add(b['$ref'][len('#/definitions/'):])
        for v in obj.values(): collect(v)
    elif isinstance(obj, list):
        for v in obj: collect(v)
collect(schema)
for name in oneof_refs:
    defn = defs.get(name, {})
    for prop_name in ('type', 'name'):
        prop = defn.get('properties', {}).get(prop_name, {})
        if 'enum' in prop and len(prop['enum']) == 1:
            d = prop.get('description', '')
            if 'discriminator' not in d.lower():
                print(f'{name}/properties/{prop_name}: {prop["enum"]}')
```

```python
# repair: annotate discriminator fields for all oneOf-referenced subtypes
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
oneof_refs = set()
def collect(obj):
    if isinstance(obj, dict):
        if 'oneOf' in obj:
            for b in obj['oneOf']:
                if '$ref' in b: oneof_refs.add(b['$ref'][len('#/definitions/'):])
        for v in obj.values(): collect(v)
    elif isinstance(obj, list):
        for v in obj: collect(v)
collect(schema)
for name in oneof_refs:
    defn = defs.get(name, {})
    for prop_name in ('type', 'name'):
        prop = defn.get('properties', {}).get(prop_name, {})
        if 'enum' in prop and len(prop['enum']) == 1:
            if 'discriminator' not in prop.get('description', '').lower():
                prop['description'] = '(discriminator)'
                print(f'Fixed: {name}/{prop_name}')
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `documentation.inlined_property_descriptions` · *advisory*

**Individual properties with non-obvious semantics carry their own `description`.**

Not every property needs a description. But properties with surprising behaviour, empirical caveats, or cross-field relationships should have inline descriptions. Examples: `Conversation.summary` (may be empty string), `Message.updated_at` (always equals `created_at`), `Citation.start_index` (character offset).

```python
# diagnostic: list all properties that have no description (for human review)
import json
with open('conversations.schema.json') as f:
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

A self-referential wrapper file provides schema-aware editing and tooltip documentation on any JSON data file without embedding a `$schema` pointer in the data file itself. The `document` field references the actual schema, so when the `null` placeholder is replaced with a real data export, VS Code validates and documents it using `conversations.schema.json`. Every `description` field in the schema surfaces as a tooltip at the corresponding location in the data.

```json
{
  "$schema": "./documenter.schema.json",
  "title": "...",
  "description": "...",
  "properties": {
    "document": { "$ref": "./conversations.schema.json" }
  },
  "document": null
}
```

---

## Empirical Grounding

### `empirical.validate_against_all_known_exports` · *enforced*

**The schema must validate against all known exports.**

Every known export is a ground-truth test case. A failing export is always a schema bug, not a data bug. New exports should be validated immediately and any failures investigated before the export is considered incorporated.

```python
# diagnostic
import json
from jsonschema import Draft4Validator
with open('conversations.schema.json') as f:
    schema = json.load(f)
for export_file in ['conversations.json']:
    with open(export_file) as f:
        data = json.load(f)
    errors = list(Draft4Validator(schema).iter_errors(data))
    if errors:
        print(f'{export_file}: {len(errors)} error(s)')
        print(f'  First: {errors[0].message}')
        print(f'  Path:  {list(errors[0].absolute_path)}')
    else:
        print(f'{export_file}: Valid')
```

```python
# repair: iterate all errors to identify what needs fixing
import json
from jsonschema import Draft4Validator
with open('conversations.schema.json') as f:
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

```python
# diagnostic: collect observed types and tool names
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

```python
# repair: mark an unevidenced branch description
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
NAME = 'ToolInputComputerUse'
schema['definitions'][NAME]['description'] = (
    'Input for the computer_use tool. '
    'Not observed in this export. '
    'See: https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool'
)
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `empirical.tool_result_id_referential_integrity` · *manual*

**Every `tool_use_id` in a `ToolResultBlock` matches the `id` of a `ToolUseBlock` in the same `content` array.**

This cross-field constraint cannot be expressed in JSON Schema draft-4. Verified empirically: zero violations across all known exports.

**Checksum:** the original export returns `945`.

```jq
# diagnostic
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

```python
# diagnostic: find null-typed definitions and properties
import json
with open('conversations.schema.json') as f:
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
print('All null-typed fields (verify each against export data):')
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
# diagnostic
jq '[.[].chat_messages[].content[] | {type, keys: keys}] | group_by(.type) |
    map({type: .[0].type,
         distinct_key_orders: (map(.keys) | unique | length)})' \
    conversations.json
```

---

## Composition Patterns

### `composition.discriminated_union_pattern` · *enforced*

**Discriminated unions follow the wrapper / base / subtype pattern.**

A discriminated union is expressed as three layers:

1. A **wrapper** schema with exactly five fields: `title`, `description`, `type`, `allOf` (base ref + `Has*DiscriminatorProperty` ref), `oneOf` (subtype refs).
2. A **`...Base`** schema with `additionalProperties: false` and all shared fields, where the discriminator field is present but its value is unconstrained.
3. **n subtype** schemas, each specifying only the discriminator field (constrained to a single `enum` value) and any per-subtype fields.

Key insight: `allOf` and `oneOf` sit at the **wrapper** level, not inside the subtypes, which avoids `additionalProperties` conflicts. The `Has*DiscriminatorProperty` schema asserts the discriminator field is `required` and typed as a string.

Known exception: `PromptContextMetadataSearch`/`Fetch` use key-presence discrimination rather than a type/name field, so no `Has*DiscriminatorProperty` applies.

```python
# diagnostic
import json
KNOWN_KEY_PRESENCE = {
    '/definitions/ToolResultSearchItem/properties/prompt_context_metadata'
}
with open('conversations.schema.json') as f:
    schema = json.load(f)
def check(obj, path=''):
    if isinstance(obj, dict):
        if ('oneOf' in obj
                and any('$ref' in b for b in obj['oneOf'])
                and path not in KNOWN_KEY_PRESENCE):
            all_of_refs = [s.get('$ref', '') for s in obj.get('allOf', [])]
            if not any('DiscriminatorProperty' in r for r in all_of_refs):
                print(f'{path}: structural oneOf without Has*DiscriminatorProperty in allOf')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)
```

```python
# repair: add Has*DiscriminatorProperty to a wrapper's allOf
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
# Example: add HasTypeDiscriminatorProperty to a wrapper
wrapper = schema['definitions']['ContentBlock']
ref = {'$ref': '#/definitions/HasTypeDiscriminatorProperty'}
if ref not in wrapper.get('allOf', []):
    wrapper.setdefault('allOf', []).append(ref)
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `composition.discriminator_values_disjoint` · *enforced*

**Discriminator enum values across all branches of a `oneOf` are mutually disjoint.**

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
def get_disc_vals(ref):
    name = ref[len('#/definitions/'):]
    for prop in defs.get(name, {}).get('properties', {}).values():
        if 'enum' in prop: return set(prop['enum'])
    return set()
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'oneOf' in obj:
            seen = set()
            for branch in obj['oneOf']:
                vals = get_disc_vals(branch.get('$ref', ''))
                overlap = seen & vals
                if overlap: print(f'{path}: overlapping discriminator values {overlap}')
                seen |= vals
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)
```

---

### `composition.base_schemas_closed` · *enforced*

**All `...Base` schemas have `additionalProperties: false`.**

The `...Base` schema is the definitive closed contract for all shared fields. Future changes to the export format are caught immediately.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    if name.endswith('Base') and defn.get('additionalProperties') is not False:
        print(f'{name}: missing additionalProperties: false')
```

```python
# repair
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
for name, defn in schema['definitions'].items():
    if name.endswith('Base') and defn.get('additionalProperties') is not False:
        defn['additionalProperties'] = False
        print(f'Fixed: {name}')
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `composition.wrapper_has_five_fields` · *enforced*

**Union wrapper schemas have exactly five fields: `title`, `description`, `type`, `allOf`, `oneOf`.**

The wrapper is a pure structural combinator with no additional constraints.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
expected = {'title', 'description', 'type', 'allOf', 'oneOf'}
for name, defn in schema['definitions'].items():
    if 'oneOf' in defn and 'allOf' in defn:
        actual = set(defn.keys())
        if actual != expected:
            print(f'{name}: fields {sorted(actual)}, expected {sorted(expected)}')
```

```python
# repair: remove unexpected fields from a wrapper (manual review recommended first)
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
expected = {'title', 'description', 'type', 'allOf', 'oneOf'}
for name, defn in schema['definitions'].items():
    if 'oneOf' in defn and 'allOf' in defn:
        extra = set(defn.keys()) - expected
        for k in extra:
            print(f'{name}: removing extra field "{k}" = {defn[k]!r}')
            del defn[k]
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `composition.no_additional_properties_on_subtypes` · *enforced*

**Subtype schemas must not combine `additionalProperties: false` with `allOf` referencing a schema that has `properties`.**

This would cause the base's properties to be rejected as "additional". The constraint belongs exclusively on the `...Base` schema. This was the key insight from the proof-of-concept.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
for name, defn in defs.items():
    if defn.get('additionalProperties') is False and 'allOf' in defn:
        for ref_obj in defn.get('allOf', []):
            ref = ref_obj.get('$ref', '')[len('#/definitions/'):]
            if ref and defs.get(ref, {}).get('properties'):
                print(f'{name}: additionalProperties:false + allOf -> {ref} (which has properties)')
```

```python
# repair: remove additionalProperties: false from the conflicting subtype
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
for name, defn in defs.items():
    if defn.get('additionalProperties') is False and 'allOf' in defn:
        for ref_obj in defn.get('allOf', []):
            ref = ref_obj.get('$ref', '')[len('#/definitions/'):]
            if ref and defs.get(ref, {}).get('properties'):
                del defn['additionalProperties']
                print(f'Fixed: {name}')
with open('conversations.schema.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### `composition.base_not_used_directly` · *enforced*

**`...Base` schemas are never referenced directly from `oneOf` lists.**

The base is an implementation detail of the wrapper. Direct `oneOf` references would bypass the discriminated union pattern.

```python
# diagnostic
import json
with open('conversations.schema.json') as f:
    schema = json.load(f)
defs = schema['definitions']
base_names = {n for n in defs if n.endswith('Base')}
def check(obj, path=''):
    if isinstance(obj, dict):
        if 'oneOf' in obj:
            for b in obj['oneOf']:
                ref = b.get('$ref', '')[len('#/definitions/'):]
                if ref in base_names:
                    print(f'{path}: Base schema {ref!r} referenced directly in oneOf')
        for k, v in obj.items(): check(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check(v, f'{path}[{i}]')
check(schema)
```

---

### `composition.use_refs_not_inline` · *advisory*

**Repeated schemas are factored into definitions and referenced via `$ref`.**

Any schema appearing more than once should be a named definition. Applied to `NullableString`, `NullableBoolean`, `Timestamp`, `Flags`, `DisplayContent`, `IntegrationName`, `IconName`, etc.

```python
# diagnostic: find identical inline schema objects appearing more than once
import json
from collections import Counter
with open('conversations.schema.json') as f:
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
# diagnostic
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

- **No `if`/`then`/`else`**: discriminated unions use `allOf`/`oneOf` wrapper/base/subtype pattern instead.
- **`$ref` siblings are ignored**: move sibling documentation into the referenced definition's `description`.
- **No `nullable` shorthand**: use `oneOf: [{type: null}, ...]` or a named `NullableString` definition.
- **No `$comment`**: use `description` for all documentation including internal notes.
- **No cross-field constraints**: document in `description` with a verification snippet.
- **No `format` enforcement**: `format: date-time` is advisory only; document regex in `description`.

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

The `Has*DiscriminatorProperty` pattern is a good example: whether it has been applied "correctly" and "completely" depends on a semantic understanding of what constitutes a union wrapper. An automated tool can check that every structural `oneOf` has a `Has*DiscriminatorProperty` in its `allOf` — but it cannot determine whether a given `oneOf` *should* have one (e.g. `PromptContextMetadata` discriminates on key presence, not a type field). The principles in this document are an attempt to capture that judgement, but they are necessarily incomplete.

**Question:** Is there a principled way to classify `oneOf` unions by their discrimination strategy (type-field, name-field, key-presence, structural) and apply different checks to each class?

---

### `open.draft7_migration` · *open*

**Should the schema be migrated to JSON Schema draft-7 or later?**

Draft-7 would enable `if`/`then`/`else` (cleaner discriminated unions), `$comment` (internal notes separate from user-facing descriptions), and `type: [string, null]` (cleaner nullable). The cost is potential loss of VS Code tooltip support.

**Questions:** Does VS Code's JSON language server support draft-7 for tooltip purposes? Would `if`/`then`/`else` actually simplify the schema significantly? Is the wrapper/base/subtype pattern still needed in draft-7?

---

### `open.toolinput_schemas_in_oneof` · *open*

**Can `ToolInput*` schemas be incorporated into the `oneOf` discriminated union?**

Currently `ToolInput*` schemas are documented but not enforced via `oneOf` because they overlap structurally. In draft-4, one approach is to fold the `input` schema directly into each `ToolUseBlock` subtype, losing the standalone `ToolInput*` definitions. In draft-7, `if`/`then`/`else` keyed on `name` would handle this cleanly.

**Question:** Is it worth restructuring the subtypes to inline their `input` schemas, even at the cost of losing standalone `ToolInput*` definitions?

---

### `open.attachment_file_type_convention` · *open*

**The `file_type` field in `Attachment` uses an inconsistent naming convention.**

Observed values include `txt` (extension-style) and `text/html` (MIME-type-style). It is unclear whether this is a server-side inconsistency or intentional.

**Question:** Is the mixed convention stable? Should the schema enumerate known values more precisely?

---

### `open.display_content_vs_api` · *open*

**The `display_content` field is a claude.ai UI addition, but its structure closely mirrors API content block types.**

It is unclear whether `display_content` is a rendering hint derived from the tool result content, or independently specified. Understanding this would help predict what new `display_content` types might appear.

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

1. Run `Draft4Validator` against the new export and note the first failing path and message.
2. Inspect the failing instance in the export to understand the new structure.
3. Determine whether this is: (a) a new field, (b) a new enum value, (c) a new `oneOf` branch, or (d) a nullable field that was previously always null.
4. Update the schema minimally to accommodate the new observation.
5. Add any new tool name to `ToolName` and create the corresponding `ToolUse`/`ToolResult` subtype pair using the repair snippet in `naming.subtype_naming_convention`.
6. Re-run validation against **all** known exports to confirm no regressions.
7. Run all `enforced` diagnostics and fix any failures — refining diagnostics first, then fixing schema issues.
8. For new tool names: check whether they are public API tools (add `See:` link) or claude.ai-internal (note as such).
9. Reapply BFS ordering using the repair snippet in `structure.bfs_order`.
10. Update this principles document if the new observation motivates a new or revised principle.

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

See repair snippet in `structure.bfs_order`.

---

*This document was developed iteratively alongside `conversations.schema.json` over multiple sessions. The schema was reverse-engineered from Claude.ai bulk data exports; all constraints are empirically grounded unless explicitly noted otherwise. The Open Questions section is intentionally incomplete — it should grow as new questions arise and shrink as decisions are made.*