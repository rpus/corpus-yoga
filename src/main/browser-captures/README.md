# browser-captures

Safari automation for exporting Claude.ai conversations as markdown and live API JSON.

Two modes — same JS ([`browser-chat-capture.js`](browser-chat-capture.js)), different scope:

| Mode | Entry point | Output |
| --- | --- | --- |
| **Shortcut** | `export.applescript` | `~/Downloads/` |
| **Pipeline** | `safari_capture.sh` | `../browser-captures/<batch>/<uuid>/` |

---

## One-time setup

**Enable JavaScript from Apple Events in Safari:**

Safari › Develop › Allow JavaScript from Apple Events

If the Develop menu is not visible: Safari › Settings › Advanced › Show features for web developers

---

## Shortcut mode

Standalone — no pipeline or data export needed.

**Scope:** `claude.ai/chat/*` (single conversation) or `claude.ai/recents` (all) — `export.applescript` detects the front tab and delegates to `export-conversation.applescript` or `export-all-conversations.applescript` accordingly. Both inject `browser-chat-capture.js` into the page, which intercepts clipboard writes to capture each message and assembles the markdown.

**Command:**

```bash
caffeinate -dim osascript "$HOME/dev/Anthropic/claude-export-yoga/export.applescript"
```

`caffeinate -dim` prevents display, idle, and disk sleep during long batch runs.
To add a keyboard shortcut: create a Shortcuts app action with the above command.

**Output:** `{name}.md` + `{name}.log` + `{uuid}.json` per conversation, in `~/Downloads/`.

**Stopping:** `pkill -f "export-all-conversations"`, or close the current Safari tab — the script errors and halts.

---

## Pipeline mode

Requires a downloaded bulk chat export in `../chat-exports/`. Safari must be open and logged in for steps 1–2.

**Scope:** a single export batch or all batches; each step accepts **ONE OF**:

1. **Capture** conversations as markdown (`safari_capture.sh` — iterates the export's `conversations.json`, navigates Safari to each conversation, and injects `browser-chat-capture.js` to capture and download the markdown):
    - `src/main/browser-captures/safari_capture.sh --chat-export  ../chat-exports/data-<...>`
    - `src/main/browser-captures/safari_capture.sh --chat-exports ../chat-exports`

2. **Fetch** live API JSON for each capture (`safari_fetch_api_json.sh`):
    - `src/main/browser-captures/safari_fetch_api_json.sh --browser-capture  ../browser-captures/data-<...>`
    - `src/main/browser-captures/safari_fetch_api_json.sh --browser-captures ../browser-captures`

3. **Validate** API JSON against the `apiConversation` schema (`RUNME.sh`):
    - `src/main/browser-captures/RUNME.sh --browser-capture  ../browser-captures/data-<...>`
    - `src/main/browser-captures/RUNME.sh --browser-captures ../browser-captures`

**Output:** `{name}.md` + `{name}.log` + `{name}.json` per conversation, in `../browser-captures/<batch>/<uuid>/`.

**Stopping:** each step runs to completion; to abort `safari_capture.sh` or `safari_fetch_api_json.sh` mid-run, close the current Safari tab.

---

## Files

### Pipeline scripts

| File | What it does |
| --- | --- |
| `safari_capture.sh` / `safari_capture.py` | Iterates a bulk export's conversations, captures each via Safari, writes `{name}.md` + `{name}.log` + `{name}.json` to `../browser-captures/<batch>/<uuid>/` |
| `safari_fetch_api_json.sh` / `safari_fetch_api_json.py` | For each capture, fetches the live API JSON from `/api/organizations/{org}/chat_conversations/{uuid}` and saves it alongside the markdown |
| `validate.sh` | Validates each `{name}.json` against `rsc/schema/browser-captures/apiConversation/` |
| `RUNME.sh` | Runs `validate.sh` for a batch or all batches |

### Shortcut mode scripts

| File | What it does |
| --- | --- |
| `export.applescript` | Dispatcher: delegates based on front tab URL |
| `export-conversation.applescript` | Exports the conversation in the current tab |
| `export-all-conversations.applescript` | Exports every conversation from `/recents` |
| `browser-chat-capture.js` | Injected into each tab; captures messages via clipboard |

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "JavaScript injection failed" | Enable Safari › Develop › Allow JavaScript from Apple Events |
| "Front tab is not a Claude.ai chat page" | Switch to a `claude.ai/chat/` tab before running |
| "Could not read browser-chat-capture.js" | Check that `browser-chat-capture.js` exists alongside the scripts |
| "No conversations found on claude.ai/recents" | Make sure you are logged in to Claude.ai in Safari |
| Files not appearing in `~/Downloads/` | Check that `~/Downloads/` is Safari's configured download location |
| "stalled — giving up" in the log | Page may not have fully rendered; the 30s stall timeout was hit |
| "Error: No copy buttons found!" | Page may not have fully rendered; try increasing the `delay 2` after page load |
