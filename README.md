# README

This repo wrangles AI conversations, from Gemini (via browser capture only) and Claude (via browser capture, bulk export, and local coding sessions).

---

```bash
# git clean -fdXn; git clean -fdxn

./RUNME.sh --capture-from-browser \
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
  - **Shortcut mode** — triggered on the current browser page; no programmatic navigation:
    - Set up a macOS Shortcuts app shortcut: `caffeinate -dim osascript "$HOME/<path-to-repo-parent>/claude-export-yoga/src/main/browser-captures/export.applescript"`
    - With front tab on a specific conversation: captures that conversation (page already loaded)
    - With front tab on <https://claude.ai/recents> or <https://gemini.google.com/app>: captures all conversations (AppleScript iterates the listing)
  - **Script mode** — Python navigates to every conversation automatically via `capture_all()`:
    - `./src/main/browser-captures/PREP.sh` (or `./RUNME.sh --capture-from-browser`)
- Render clean markdown straight from the captured API JSON — no browser, no DOM scrape (preferred over the Safari markdown capture above; it only needs the `apiConversation` JSON each capture already fetches):
  - `src/run_python_script.sh src/main/browser-captures/project_markdown.py --browser-captures ext/browser-captures/claude --out gen/browser-captures/markdown`
  - Projects each capture to the lean `markdownConversation` shape, validates it, and writes a flat directory of `<title>.md` with sane titles.
  - Verify the projection reproduces (or improves on) the legacy scrape — the safety net before retiring it: `src/run_python_script.sh src/main/browser-captures/compare_markdown.py --browser-captures ext/browser-captures/claude` (add `--diff` for full per-conversation diffs).
- Browse and read captures as rendered markdown + LaTeX:
  - `src/main/model/serve_markdown.sh --browser-captures ext/browser-captures/claude --daemon` then open <http://localhost:8182>
  - `src/main/model/serve_markdown.sh stop` to shut down

---

## Pre-public checklist

- [ ] Create a new repo (to get clean/sane git history).
- [ ] Add a LICENSE file.
- [ ] `src/main/schema_recommendations.py` — all 9 checks are stubbed; once implemented, call it from all pipeline `validate.sh` scripts on validation success
