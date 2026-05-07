# browser-captures — Safari automation

AppleScript automation for running `browser-chat-capture.js` in Safari without opening the developer console.

## Files

- `export.applescript` — dispatcher: delegates to the right script based on the front tab URL
- `export-conversation.applescript` — exports the conversation in the current Safari tab
- `export-all-conversations.applescript` — exports every conversation, one tab at a time
- `browser-chat-capture.js` — injected into each tab; captures messages via clipboard interception and downloads `{name}.md` + `{name}.log`
- `safari_capture.sh` / `safari_capture.py` — pipeline entry point: iterates a bulk export's `conversations.json`, calls `export-conversation.applescript` per UUID, moves output to `../browser-captures/`

## One-time setup

**Enable JavaScript from Apple Events in Safari:**

Safari › Develop › Allow JavaScript from Apple Events

If the Develop menu is not visible: Safari › Settings › Advanced › Show features for web developers

## Usage

### Export the current conversation

1. Open the Claude.ai conversation you want to export in Safari (front tab)
2. Run `export.applescript` (or `export-conversation.applescript` directly)

The front tab must be on a `https://claude.ai/chat/` URL; the script alerts and exits if not.
Output goes to `~/Downloads/` as `{name}.md` and `{name}.log`.

### Export all conversations (shortcut mode)

1. Open `https://claude.ai/recents` in Safari (front tab)
2. Run `export.applescript` (or `export-all-conversations.applescript` directly)
3. Confirm the count in the dialog
4. Safari opens each conversation in a new tab, downloads `.md` and `.log` to `~/Downloads/`, and closes the tab

Both scripts read `browser-chat-capture.js` from the same directory at run time, so changes to the JS are picked up automatically.

### Running the scripts

- Open in Script Editor and click Run
- Save as an Application (File › Export › File Format: Application) and double-click
- Trigger via the Shortcuts app (see below)

#### Shortcuts app (recommended for keyboard shortcut)

Add a "Run Shell Script" action. Use `export.applescript` for a single shortcut that works on both pages:

```bash
caffeinate -dim osascript "$HOME/dev/Anthropic/claude-export-yoga/src/main/browser-captures/export.applescript"
```

Then assign a keyboard shortcut in the shortcut's Details panel. `caffeinate -dim` prevents display, idle, and disk sleep during long batch runs.

### Stopping a batch run

To stop `export-all-conversations.applescript` mid-run:

```bash
pkill -f "export-all-conversations"
```

Or close the currently open Safari tab — the script will error and halt on the next iteration.

## What each script does

### `export.applescript`

Checks the front tab URL and delegates:

- `https://claude.ai/chat/*` → `export-conversation.applescript`
- `https://claude.ai/recents` → `export-all-conversations.applescript`
- Anything else → alert

### `export-conversation.applescript`

1. Checks the front tab URL starts with `https://claude.ai/chat/`
2. Reads and injects `browser-chat-capture.js` into the tab
3. The JS captures each message by clicking copy buttons and intercepting the clipboard, builds markdown, and downloads `{name}.md` and `{name}.log` to `~/Downloads/`

### `export-all-conversations.applescript`

1. Checks the front tab URL starts with `https://claude.ai/recents`
2. Clicks "Show more" until all conversations are loaded into the DOM
3. Extracts all unique conversation UUIDs and names from the chat links
4. Shows a confirmation dialog with the count
5. For each conversation: opens `https://claude.ai/chat/{uuid}` in a new tab, waits for React to render, runs `export-conversation.applescript`, polls the status div for completion (bails after 30s stall), logs the result, then closes the tab

Output goes to `~/Downloads/` as flat files. Log is appended to `claude-export.log` in the same directory as the scripts.

Log format:

```text
2026-05-04 14:23:45 === 55 conversations ===
2026-05-04 14:23:46    1/55 | <uuid> | <name>
2026-05-04 14:23:46    opening
2026-05-04 14:23:52    running export
2026-05-04 14:24:07    ✅ Downloaded: filename.md
2026-05-04 14:24:07    json: filename.json
```

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
