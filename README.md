# README

This repo wrangles AI conversations, from Gemini (via browser capture only) and Claude (via browser capture, bulk export, and local coding sessions).

---

```bash
# git clean -fdXn; git clean -fdxn

./RUNME.sh --browser-captures \
  --pay-for-inference # (requires `ANTHROPIC_API_KEY` in `env`)

./src/main/model/gen_model.sh

# ./src/test/pre_commit.sh
```

## How to use

- Prepare new data
  - Open Safari, log in to <https://claude.ai>
  - Ask to "Export ('All') data" from <https://claude.ai/settings/data-privacy-controls>
  - Click on 24-hour emailed "Download Data" link (like <https://claude.ai/export/0fc4c1e0-4719-4e10-997a-697bf05599af/download/cdb658167a0d6dd4a2ffe829aeea9d15>)
  - Move downloaded folder/zip (like `data-*`) from `Downloads` into the `ext/chat-exports` in this (cloned) repo, and unzip it if needed.
  - `export ANTHROPIC_API_KEY=<your-key>` (required for table inference by Claude)
- Capture markdown exports for each conversation via Safari (optional pre-processing step):
  - Open Safari, log in to <https://claude.ai> or <https://gemini.google.com>
  - **Shortcut mode** (moves captures directly into `ext/`, same as script mode; `.log` files stay in `~/Downloads/`):
    - Set up a Shortcuts app shortcut: `caffeinate -dim osascript "$HOME/<path-to-repo-parent>/claude-export-yoga/src/main/browser-captures/export.applescript"`
    - With front tab on <https://claude.ai/recents> or <https://gemini.google.com/app>: exports all conversations
    - With front tab on a specific conversation: exports that conversation
  - **Script mode** (moves captures directly into `ext/`; `--discover` finds all from recents, `--recapture` re-runs known UUIDs only):
    - `./src/main/browser-captures/claude/safari_capture.sh --discover`
    - `./src/main/browser-captures/gemini/safari_capture.sh --discover`
- Fetch live API JSON for existing captures without it (for apiConversation schema validation):
  - `./src/main/browser-captures/claude/safari_fetch_api_json.sh`
  - Saves `{title}.json` alongside each capture
- Browse and read captures as rendered markdown + LaTeX:
  - `src/main/model/serve_markdown.sh --browser-captures ext/browser-captures/claude --daemon` then open <http://localhost:8182>
  - `src/main/model/serve_markdown.sh stop` to shut down

---

## Pre-public checklist

- [ ] Create a new repo (to get clean/sane git history).
- [ ] Add a LICENSE file.
- [ ] `src/main/schema_recommendations.py` — all 9 checks are stubbed; once implemented, call it from all pipeline `validate.sh` scripts on validation success
