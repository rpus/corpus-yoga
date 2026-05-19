# README

This repo wrangles Claude data exports.

```bash
# git clean -fdX; git clean -fdxn
./RUNME.sh \
  --pay-for-inference # (requires `ANTHROPIC_API_KEY` in `env`)
./src/main/model/gen_model.sh
# ./src/test/pre_commit.sh
```

## How to use

- Prepare new data
  - Open Safari, log in to <https://claude.ai>
  - Ask to "Export ('All') data" from <https://claude.ai/settings/data-privacy-controls>
  - Click on 24-hour emailed "Download Data" link (like <https://claude.ai/export/0fc4c1e0-4719-4e10-997a-697bf05599af/download/cdb658167a0d6dd4a2ffe829aeea9d15>)
  - Move downloaded folder (like `data-*`) from `Downloads` into the `chat-exports` sibling directory of this (current) directory.
  - `export ANTHROPIC_API_KEY=<your-key>` (required for table inference by Claude)
- Capture markdown exports for each conversation via Safari (optional pre-processing step):
  - Open Safari, log in to <https://claude.ai>
  - **Shortcut mode** (standalone, outputs `.md` + `.log` + `{uuid}.json` to `~/Downloads/`):
    - Set up a Shortcuts app shortcut: `caffeinate -dim osascript "$HOME/<path-to-repo-parent>/claude-export-yoga/src/main/browser-captures/export.applescript"`
    - With front tab on <https://claude.ai/recents>: exports all conversations
    - With front tab on `https://claude.ai/chat/{uuid}`: exports that conversation
  - **Pipeline mode** (re-captures all conversations in `ext/browser-captures/`):
    - `./src/main/browser-captures/safari_capture.sh --browser-captures ext/browser-captures`
- Fetch live API JSON for existing captures without it (for apiConversation schema validation):
  - `./src/main/browser-captures/safari_fetch_api_json.sh --browser-captures ext/browser-captures`
  - Saves `{title}.json` alongside each capture
- Browse and read captures as rendered markdown + LaTeX:
  - `src/main/model/serve_markdown.sh --browser-captures ext/browser-captures --daemon` then open <http://localhost:8182>
  - `src/main/model/serve_markdown.sh stop` to shut down

---

## Pre-public checklist

- [ ] Add a LICENSE file before making the repo public.
- [ ] `src/main/schema_recommendations.py` — all 9 checks are stubbed. Script is pipeline-agnostic (correct location). Once implemented, call it from all three pipeline `validate.sh` scripts on validation success.
