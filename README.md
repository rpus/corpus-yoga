# README

This repo wrangles Claude data exports.

## Prerequisites

- `python3` (e.g. `brew install python`)
- `python3 -m venv ~/venvs/general && pip install -r src/requirements.txt`

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
src/run_python_script.sh src/test/code-projects/debug_code_session_record.py ../code-projects/{project-slug}/{session}.jsonl
./src/test/pre_commit.sh
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

## Repo layout

```text
claude-export-yoga/
├── RUNME.sh                                    # run all three pipelines
├── README.md                                   # usage, prerequisites, how-to (this file)
├── ABOUT.md                                    # architecture overview: inputs, pipelines, schemas, output
├── CONTRIBUTING.md                             # project rules for contributors and Claude
├── TODO.md                                     # live capture: discoveries and pending work
│
├── src/
│   ├── main/
│   │   ├── browser-captures/
│   │   │   ├── RUNME.sh                        # validate all browser-captured API JSON
│   │   │   ├── validate.sh                     # per-batch validation
│   │   │   ├── export.applescript              # Safari automation dispatcher (shortcut mode)
│   │   │   ├── safari_capture.sh               # pipeline-mode bulk capture
│   │   │   └── safari_fetch_api_json.sh        # fetch live API JSON for existing captures
│   │   ├── chat-exports/
│   │   │   ├── RUNME.sh                        # validate + extract + present
│   │   │   ├── validate.sh                     # JSON Schema validation
│   │   │   ├── extract_files.sh                # recover files from create_file tool calls
│   │   │   ├── extract_heredocs.sh             # recover files from bash heredocs
│   │   │   ├── audit_files.sh                  # cross-reference all file sources
│   │   │   ├── infer_tables.sh                 # Claude API: categories + semantic tags (costs money)
│   │   │   └── present.sh                      # assemble self-contained HTML dashboard
│   │   ├── code-projects/
│   │   │   ├── RUNME.sh                        # convert .jsonl → JSON + validate all sessions
│   │   │   ├── validate.sh                     # per-project/session validation + titled symlink
│   │   │   └── jsonl_to_json.py                # JSONL → JSON array; writes session.json.title
│   │   ├── model/
│   │   │   ├── gen_model.sh                    # regenerate rsc/schema/model.json
│   │   │   └── search_proxy.sh                 # local markdown/LaTeX browser (port 8182)
│   │   ├── validate.py                         # shared JSON Schema validator
│   │   ├── validate_versions.sh                # validate one file against all v*.json
│   │   └── schema_recommendations.py           # post-validation schema quality hints
│   │
│   └── test/
│       ├── pre_commit.sh                       # pre-commit hook: run, stage, run; idempotency check
│       ├── pre_commit.py                       # full check suite; score in pre_commit_expected_score
│       ├── pre_commit.log                      # committed output — read changes via git diff
│       ├── xref.sh / xref.py / xref.csv        # cross-reference audit — read changes via git diff
│       ├── gen_changelog_matrix.py             # update CHANGELOG matrix from gen/ logs (append-only)
│       ├── diagnostics/                        # 25 atomic schema quality checks (one per principle)
│       ├── repairs/                            # paired auto-repair scripts for fixable diagnostics
│       └── code-projects/
│           ├── debug_code_session_record.py    # diagnose why a record fails validation
│           └── survey_code_session.py          # survey record types in a session file
│
├── rsc/
│   ├── schema/
│   │   ├── browser-captures/apiConversation/   # v1.json · principles · workflow · CHANGELOG · README
│   │   │                                       #   + api-conversation-schema.md · research.md
│   │   ├── chat-exports/conversations/         # v1–v7   · principles · workflow · CHANGELOG · README
│   │   │                                       #   + conversations-schema.md
│   │   ├── chat-exports/{memories,projects,users}/  # v1.json each
│   │   ├── code-projects/session/              # v1–v3   · principles · workflow · CHANGELOG · README
│   │   │                                       #   + session-schema.md · research.md · claude-home-directory.md
│   │   ├── principles.md                       # shared design principles for all schemas
│   │   ├── workflow.md                         # shared base: four principles · versioning · meta-rules
│   │   ├── model_join.csv                      # four-way field map: conversations ↔ session ↔ apiConversation ↔ MCP
│   │   ├── documenter.json                     # VS Code tooltip wrapper for data files
│   │   └── model.json                          # cross-pipeline type reference
│   ├── artifacts/downloaded/                   # ground-truth recovered files (never edit in place)
│   └── snippets.md                             # jq recipes: redaction, summarisation, inspection
│
└── gen/                                        # all generated output (gitignored)
    ├── browser-captures/{batch}/{uuid}/        # validation logs
    ├── chat-exports/{export}/                  # validation + extraction + presentation
    └── code-projects/{project}/{session}/      # session.json · titled symlink · validation logs
```
