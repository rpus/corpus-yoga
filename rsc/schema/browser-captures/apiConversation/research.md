# browser-captures — Research Notes

How the live claude.ai API format was discovered, captured, and incorporated into the schema.

---

## The endpoint

When claude.ai loads a conversation it calls an internal endpoint:

```http
GET /api/organizations/{org-uuid}/chat_conversations/{conversation-uuid}
    ?tree=true&rendering_mode=messages&render_all_tools=true
```

The response is a JSON object conforming to `rsc/schema/browser-captures/apiConversation/v1.json`. This is the
same data the UI renders, but with the client-side envelope fields stripped — it is
significantly leaner than the bulk export format.

The `org-uuid` is available from the cookie `lastActiveOrg`. The `conversation-uuid`
is the last path component of the conversation URL.

---

## Discovery method

The endpoint was found by:

1. Opening Safari DevTools → Network tab
2. Navigating to a conversation on claude.ai
3. Filtering for XHR/Fetch requests matching `/chat_conversations/`
4. Inspecting the response payload

The query parameters (`tree=true`, `rendering_mode=messages`, `render_all_tools=true`)
were identified as required for the full message tree with tool call details.

---

## Capture setup

Two scripts handle capture:

### `safari_capture.sh` — markdown capture

```bash
src/main/browser-captures/safari_capture.sh --chat-export ../chat-exports/data-<...>
```

Iterates all conversation UUIDs in a chat-export batch, navigates Safari to each
conversation on claude.ai, and injects `browser-chat-capture.js` to render and
download a markdown transcript. Output: `../browser-captures/{batch}/{uuid}/{title}.md`
and `{title}.log`.

Requires: Safari open and logged into claude.ai, `caffeinate` keeps the session alive.

### `safari_fetch_api_json.sh` — API JSON capture

```bash
src/main/browser-captures/safari_fetch_api_json.sh --browser-capture ../browser-captures/data-<...>
```

For each UUID directory that has a markdown capture but no JSON file, navigates Safari
to the conversation and injects a JavaScript snippet that:

1. Reads `lastActiveOrg` from the cookie
2. Extracts the conversation UUID from the URL
3. Calls the API endpoint with `credentials: 'include'` (reuses the browser session)
4. Downloads the JSON response as `{uuid}.json`

The downloaded file is then moved from `~/Downloads/` into the capture directory and
renamed to `{title}.json`.

---

## Output structure

```text
../browser-captures/
└── {export-batch}/                          ← same name as the chat-export batch
    └── {conversation-uuid}/
        ├── {title}.md                       ← markdown transcript
        ├── {title}.log                      ← capture log
        └── {title}.json                     ← live API JSON (apiConversation schema)
```

After running `validate.sh`, gen/ mirrors the input structure:

```text
gen/browser-captures/
└── {export-batch}/
    └── {conversation-uuid}/
        └── validation/
            └── apiConversation/
                └── v1.log
```

---

## Key differences from bulk export

The live API format is notably leaner than `conversations.json`:

- **No always-null envelope fields** — `flags`, `mcp_server_url`, `approval_options`,
  `approval_key`, `is_mcp_app`, `context` are all present in bulk export (always null);
  absent from the API response
- **Citations present** — `ApiCitation` objects carry `title`, `url`, `metadata`,
  `sources`; stripped from bulk export
- **`account` absent** — bulk export includes `account` metadata; API response does not
- **`stop_reason` present** — on assistant messages; stripped from bulk export
- **`index` present** — zero-based message position; no bulk export counterpart

See `rsc/schema/model_join.csv` for the full field-level comparison.

---

## Schema development

The schema was developed iteratively:

1. Captured 55 conversations from a single export batch
2. Ran `src/main/validate.py` against each with a draft schema
3. Expanded definitions to cover observed fields and tool types
4. Validated all 55 pass — results recorded in `rsc/schema/browser-captures/apiConversation/CHANGELOG.md`

The `NamespacedToolName` constraint (`not: {$ref: ToolName}`) ensures MCP-namespaced
tool names (`integration:tool`) are distinguished from built-in tool names even though
both satisfy the same string pattern.
