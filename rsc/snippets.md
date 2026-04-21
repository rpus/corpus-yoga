# Snippets

## number of (Conversation) elements in root array

```bash
jq 'length' conversations.json 
```

## redact non-empty "text" string fields

```bash
jq 'walk(if type == "object" and has("text") and .text != "" and (.text | type) == "string" then .text = "[redacted]" else . end)' conversations.json > ./gen/redacted/conversations.json
```

## project out summaries, ordered by conversation creation time

```bash
jq '[sort_by(.created_at) | to_entries[] | {key: (.key | tostring), value: .value.summary}] | from_entries' conversations.json > ./gen/summarised/conversations.json
```

## first-class definitions without a "type" member

```bash
jq '[.definitions | to_entries[] | select(.value.type == null) | .key]' ../conversations.schema.json
```

## first-class definitions without a "type" member but with a "oneOf"

```bash
jq '[.definitions | to_entries[] | select(.value.oneOf != null and .value.type == null) | .key]' ../conversations.schema.json
```

## distinct values for "key_name" keys (at any depth in document)

```bash
jq --arg key "key_name" '[.. | objects | select(has($key)) | .[$key]] | unique' conversations.json
```

## distinct values for keys at path() $p

```bash
jq '[path(.[].chat_messages[].content[].name?) as $p | getpath($p)] | unique' conversations.json
```

## "properties" not "required" or vice versa

```bash
jq '[.definitions | to_entries[] |
  select(.value.properties != null and .value.required != null) |
  .key as $def |
  (.value.properties | keys) as $props |
  (.value.required) as $req |
  {
    def: $def,
    in_props_not_required: ($props | map(select(. as $p | $req | index($p) == null))),
    in_required_not_props: ($req | map(select(. as $r | $props | index($r) == null)))
  } |
  select(.in_props_not_required != [] or .in_required_not_props != [])
]' ../conversations.schema.json
```

## "properties" not "required" (output to be manually completed before its use by `generate_optional_check.py`)

```bash
jq '[.definitions | to_entries[] |
  select(.value.properties != null and .value.required != null) |
  .key as $def |
  (.value.properties | keys) as $props |
  (.value.required) as $req |
  ($props | map(select(. as $p | $req | index($p) == null))) as $optional |
  select($optional | length > 0) |
  {
    def: $def,
    label: null,
    data_path: null,
    filter: null,
    inner_filter: null,
    optional_fields: $optional
  }
]' ../conversations.schema.json
```

## verbosity

```bash
jq '
  [.[] | {
    name: .name,
    uuid: .uuid,
    human_chars: (
      [.chat_messages[] | select(.sender == "human") |
       .content[] | select(.type == "text") | .text | length] | add // 0
    ),
    assistant_chars: (
      [.chat_messages[] | select(.content != null) | select(.sender == "assistant") |
       .content[] | select(.type == "text") | .text | length] | add // 0
    )
  } | . + {
    ratio: (if .human_chars > 0 then (.assistant_chars / .human_chars * 100 | round) / 100 else null end)
  }]
' conversations.json
```
