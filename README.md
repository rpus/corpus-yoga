# README

This repo wrangles Claude data exports.

## Prerequisites

- `python` (e.g. `brew install python`)
- `python3 -m venv ~/venvs/general && pip install -r requirements.txt`

## How to use

- Prepare new data
  - Open Safari, log in to <https://claude.ai>
  - Ask to "Export ('All') data" from <https://claude.ai/settings/data-privacy-controls>
  - Click on 24-hour emailed "Download Data" link (like <https://claude.ai/export/0fc4c1e0-4719-4e10-997a-697bf05599af/download/cdb658167a0d6dd4a2ffe829aeea9d15>)
  - Move downloaded folder (like `data-*`) from `Downloads` into the `chat-exports` sibling directory of this (current) directory.
  - `source ~/.zprofile` (to get `ANTHROPIC_API_KEY` into `env` for table inference by Claude)
- Capture markdown exports for each conversation via Safari (optional pre-processing step):
  - Open Safari, log in to <https://claude.ai>
  - **Shortcut mode** (standalone, outputs `.md` + `.log` + `{uuid}.json` to `~/Downloads/`):
    - Set up a Shortcuts app shortcut: `caffeinate -dim osascript "$HOME/dev/Anthropic/claude-export-yoga/src/main/browser-captures/export.applescript"`
    - With front tab on <https://claude.ai/recents>: exports all conversations
    - With front tab on `https://claude.ai/chat/{uuid}`: exports that conversation
  - **Pipeline mode** (scope-constrained to a bulk export, outputs to `../browser-captures/<export-name>/<uuid>/`):
    - `./src/main/browser-captures/safari_capture.sh --chat-export ../chat-exports/data-<...>`
- Fetch live API JSON for existing captures without it (for apiConversation schema validation):
  - `./src/main/browser-captures/safari_fetch_api_json.sh --browser-capture ../browser-captures/data-<...>`
  - Saves `{title}.json` alongside each capture
- Browse and read captures as rendered markdown + LaTeX:
  - `src/main/model/search_proxy.sh --daemon` then open <http://localhost:8182>
  - `src/main/model/search_proxy.sh stop` to shut down

```bash
# git clean -fdX; git clean -fdxn
./src/main/browser-captures/RUNME.sh --browser-captures ../browser-captures
./src/main/chat-exports/RUNME.sh --chat-exports ../chat-exports \
  --pay-for-inference # (requires `ANTHROPIC_API_KEY` in `env`)
./src/main/code-projects/RUNME.sh --code-projects ../code-projects
./src/main/model/gen_model.sh
# ./src/test/pre_commit.sh
```

## What that does

- Validate the data
  - `./src/main/chat-exports/RUNME.sh --chat-exports ../chat-exports` (or `validate.sh --chat-export <one-export>`)
- Address any errors by updating/retesting the schemas (in `./rsc/schema`) and tooling (in `./src/main`) as needed.
- Extract files and heredocs
  - `./src/main/chat-exports/extract_files.sh --chat-exports ../chat-exports`
  - `./src/main/chat-exports/extract_heredocs.sh --chat-exports ../chat-exports`
- Present the data
  - `./src/main/chat-exports/infer_tables.sh --chat-exports ../chat-exports`
  - NB the above call requires an Anthropic API key and costs money.
  - `./src/main/chat-exports/present.sh --chat-exports ../chat-exports`

---

## Schema maintenance

When any pipeline schema changes, regenerate the model candidates and review `rsc/schema/model.json`:

```bash
./src/main/model/gen_model.sh
```

When a new Claude Code session appears in `../code-projects/` or `rsc/schema/code-projects/session/v1.json` changes, follow the validation loop in `rsc/schema/code-projects/session/workflow.md`. In brief:

```bash
./src/main/code-projects/RUNME.sh
# if a record fails:
python src/test/code-projects/debug_code_session_record.py ../code-projects/{project-slug}/{session}.jsonl
python src/test/pre_commit.py
```

---

## To be tested

- Process `conversations.json` using the redaction snippet in `rsc/snippets.md`.
  - `mkdir ./gen/chat-exports/data-*/redacted`
- Process `conversations.json` using the summarisation snippet in `rsc/snippets.md`.
  - `mkdir ./gen/chat-exports/data-*/summarised`

## To be implemented

- Make a `chat_links.json` file to hold public viewing links for each chat.
- Make a `summaries.md` file (from browser-captures output).
- Make a `memory.md`.
- Make an output/files directory.

---

## Documentation

### Project

| Document | Description |
| --- | --- |
| [`doc/README.md`](doc/README.md) | Architecture overview: inputs, pipelines, schemas, output structure, provenance; index of all sub-documents |
| [`doc/pipeline-model.md`](doc/pipeline-model.md) | All pipelines and schemas as a comparative table; guide for adding a new pipeline |
| [`doc/chat-exports/conversations-schema.md`](doc/chat-exports/conversations-schema.md) | Deep-dive on `rsc/schema/chat-exports/conversations/`: versioning, format comparison, workflow summary, MCP correspondence |
| [`doc/browser-captures/api-conversation-schema.md`](doc/browser-captures/api-conversation-schema.md) | Reference for `rsc/schema/browser-captures/apiConversation/`: structure, differences from bulk export, tool blocks |
| [`doc/browser-captures/research.md`](doc/browser-captures/research.md) | How the live API endpoint was discovered and captured; capture setup and output structure |
| [`doc/code-projects/session-schema.md`](doc/code-projects/session-schema.md) | Reference for `rsc/schema/code-projects/session/`: the nine record types, turn envelope, content blocks, MCP mapping |
| [`doc/code-projects/research.md`](doc/code-projects/research.md) | How the CLI session format was reverse-engineered; `../code-projects/` setup procedure |
| [`doc/code-projects/claude-home-directory.md`](doc/code-projects/claude-home-directory.md) | Directory-by-directory reference for `~/.claude/` and `~/.claude.json` |
| [`doc/code-projects/investigation-methodology.md`](doc/code-projects/investigation-methodology.md) | How to reverse-engineer an undocumented directory; reusable beyond this project |
| [`src/main/code-projects/RUNME.sh`](src/main/code-projects/RUNME.sh) | Entry point: validate Claude Code CLI session transcripts against the session schema |
| [`src/test/code-projects/survey_code_session.py`](src/test/code-projects/survey_code_session.py) | Survey record types and field structure of session files (used during schema development) |
| [`src/test/code-projects/debug_code_session_record.py`](src/test/code-projects/debug_code_session_record.py) | Diagnose why a specific record fails validation: tests each `Record.oneOf` branch and drills into the matching subtype |

### Schema

| Document | Description |
| --- | --- |
| [`rsc/schema/chat-exports/conversations/principles.md`](rsc/schema/chat-exports/conversations/principles.md) | Every design rule for the conversations schema, with diagnostic/repair scripts and inline snippets |
| [`rsc/schema/chat-exports/conversations/workflow.md`](rsc/schema/chat-exports/conversations/workflow.md) | 11-step loop for incorporating new exports and making schema changes |
| [`rsc/schema/chat-exports/conversations/CHANGELOG.md`](rsc/schema/chat-exports/conversations/CHANGELOG.md) | Version history and export compatibility matrix |
| [`rsc/schema/chat-exports/conversations/README.md`](rsc/schema/chat-exports/conversations/README.md) | Format comparison: CLI `.jsonl` vs claude.ai export |
| [`rsc/schema/code-projects/session/README.md`](rsc/schema/code-projects/session/README.md) | CLI session schema at a glance: record types, content blocks, MCP mapping table |
| [`rsc/schema/code-projects/session/principles.md`](rsc/schema/code-projects/session/principles.md) | Schema design principles: defers to conversations/principles.md; documents justified deviations |
| [`rsc/schema/code-projects/session/workflow.md`](rsc/schema/code-projects/session/workflow.md) | Validation loop, `model_join.csv` maintenance, versioning, real-time vs snapshot lifecycle |
| [`rsc/schema/code-projects/session/CHANGELOG.md`](rsc/schema/code-projects/session/CHANGELOG.md) | Version history and session coverage matrix |
| [`rsc/schema/browser-captures/apiConversation/principles.md`](rsc/schema/browser-captures/apiConversation/principles.md) | Schema design principles: defers to conversations/principles.md; documents apiConversation-specific deviations |
| [`rsc/schema/browser-captures/apiConversation/workflow.md`](rsc/schema/browser-captures/apiConversation/workflow.md) | Validation loop and maintenance workflow for the live API conversation schema |
| [`rsc/schema/browser-captures/apiConversation/CHANGELOG.md`](rsc/schema/browser-captures/apiConversation/CHANGELOG.md) | Version history and capture coverage matrix |
| [`rsc/schema/browser-captures/apiConversation/README.md`](rsc/schema/browser-captures/apiConversation/README.md) | API conversation schema at a glance: root type, message/content structure, comparison with bulk-export format |
| [`rsc/schema/model_join.csv`](rsc/schema/model_join.csv) | Unified four-way field correspondence table: conversations ↔ session ↔ apiConversation ↔ MCP |
| [`src/test/diagnostics/README.md`](src/test/diagnostics/README.md) | All diagnostic scripts: what each checks, which have a paired repair script |
| [`src/test/repairs/README.md`](src/test/repairs/README.md) | All 14 repair scripts: what each fixes, usage notes |

### Reference

| Document | Description |
| --- | --- |
| [`rsc/snippets.md`](rsc/snippets.md) | jq recipes: redaction, summarisation, frequency analysis, export inspection |
| [`src/test/xref.sh`](src/test/xref.sh) | Cross-reference audit: scans all source files for inter-file links, flags missing targets and unreferenced files |
