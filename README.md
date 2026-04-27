# README

This repo wrangles Claude data exports.

## Prerequisites

- python

## How to use

- Prepare new data
  - Ask to "Export ('All') data" from <https://claude.ai/settings/data-privacy-controls>
  - Click on 24-hour emailed "Download Data" link (like <https://claude.ai/export/0fc4c1e0-4719-4e10-997a-697bf05599af/download/cdb658167a0d6dd4a2ffe829aeea9d15>)
  - Move downloaded folder (like `data-*`) from `Downloads` into the `conversation-exports` sibling directory of this (current) directory.
  - `source ~/.zprofile` (to get `ANTHROPIC_API_KEY` into `env` for table inference by Claude)

```bash
./src/main/conversation-exports/RUNME.sh --conversation-exports ../conversation-exports
./src/test/conversation-exports/audit_files.sh --conversation-exports ../conversation-exports
./src/main/code-projects/RUNME.sh --code-projects ../code-projects
./src/test/xref.sh
./src/test/pre_commit.sh
git clean -fdX; git clean -fdxn
```

## What that does

- Validate the data
  - `./src/main/conversation-exports/validate.sh --conversation-exports ../conversation-exports`
- Address any errors by updating/retesting the schemas (in `./rsc/schema`) and tooling (in `./src/main`) as needed.
- Extract files and heredocs
  - `./src/main/conversation-exports/extract_files.sh --conversation-exports ../conversation-exports`
  - `./src/main/conversation-exports/extract_heredocs.sh --conversation-exports ../conversation-exports`
- Present the data
  - `./src/main/conversation-exports/infer_tables.sh --conversation-exports ../conversation-exports`
  - NB the above call requires an Anthropic API key and costs money.
  - `./src/main/conversation-exports/present.sh --conversation-exports ../conversation-exports`

---

## Schema maintenance

When the conversations schema changes, regenerate the model candidates and review `rsc/model.json`:

```bash
./src/test/gen_model.sh
```

When a new Claude Code session appears in `../code-projects/` or `rsc/schema/sessions/v1.json` changes, follow the validation loop in `rsc/schema/sessions/workflow.md`. In brief:

```bash
./src/main/code-projects/RUNME.sh
# if a record fails:
python src/test/code-projects/debug_code_session_record.py ../code-projects/{project-slug}/{session}.jsonl
python src/test/pre_commit.py
```

---

## To be tested

- Process `conversations.json` using the redaction snippet in `rsc/snippets.md`.
  - `mkdir ./gen/conversation-exports/data-*/redacted`
- Process `conversations.json` using the summarisation snippet in `rsc/snippets.md`.
  - `mkdir ./gen/conversation-exports/data-*/summarised`

## To be implemented

- Make a `chat_links.json` file to hold public viewing links for each chat.
- Make a `summaries.md` file (using claude-chat-exporter).
- Make a `memory.md`.
- Make an output/files directory.

---

## Documentation

### Project

| Document | Description |
| --- | --- |
| [`doc/README.md`](doc/README.md) | Index and orientation guide for the `doc/` directory |
| [`doc/project-overview.md`](doc/project-overview.md) | Architecture: pipeline stages, artifact recovery, all schemas, output structure, provenance |
| [`doc/conversation-exports/conversations-schema.md`](doc/conversation-exports/conversations-schema.md) | Deep-dive on `rsc/schema/conversations/`: versioning, format comparison, workflow summary, MCP correspondence |
| [`doc/code-projects/sessions-schema.md`](doc/code-projects/sessions-schema.md) | Reference for `rsc/schema/sessions/`: the nine record types, turn envelope, content blocks, MCP mapping |
| [`doc/code-projects/research.md`](doc/code-projects/research.md) | How the CLI session format was reverse-engineered; `../code-projects/` setup procedure |
| [`src/main/code-projects/RUNME.sh`](src/main/code-projects/RUNME.sh) | Entry point: validate Claude Code CLI session transcripts against the sessions schema |
| [`src/test/code-projects/survey_code_session.py`](src/test/code-projects/survey_code_session.py) | Survey record types and field structure of session files (used during schema development) |
| [`src/test/code-projects/debug_code_session_record.py`](src/test/code-projects/debug_code_session_record.py) | Diagnose why a specific record fails validation: tests each `Record.oneOf` branch and drills into the matching subtype |

### Schema

| Document | Description |
| --- | --- |
| [`rsc/schema/conversations/principles.md`](rsc/schema/conversations/principles.md) | Every design rule for the conversations schema, with diagnostic/repair scripts and inline snippets |
| [`rsc/schema/conversations/workflow.md`](rsc/schema/conversations/workflow.md) | 11-step loop for incorporating new exports and making schema changes |
| [`rsc/schema/conversations/CHANGELOG.md`](rsc/schema/conversations/CHANGELOG.md) | Version history and export compatibility matrix |
| [`rsc/schema/conversations/README.md`](rsc/schema/conversations/README.md) | Format comparison: CLI `.jsonl` vs claude.ai export |
| [`rsc/schema/sessions/README.md`](rsc/schema/sessions/README.md) | CLI sessions schema at a glance: record types, content blocks, MCP mapping table |
| [`rsc/schema/sessions/principles.md`](rsc/schema/sessions/principles.md) | Schema design principles: defers to conversations/principles.md; documents justified deviations |
| [`rsc/schema/sessions/workflow.md`](rsc/schema/sessions/workflow.md) | Validation loop, `cli_join.csv` maintenance, versioning, real-time vs snapshot lifecycle |
| [`rsc/schema/sessions/CHANGELOG.md`](rsc/schema/sessions/CHANGELOG.md) | Version history and session coverage matrix |
| [`rsc/schema/sessions/cli_join.csv`](rsc/schema/sessions/cli_join.csv) | Field-level correspondence table: CLI sessions ↔ conversations export ↔ MCP protocol |
| [`src/test/diagnostics/README.md`](src/test/diagnostics/README.md) | All 26 diagnostic scripts: what each checks, which have a paired repair script |
| [`src/test/repairs/README.md`](src/test/repairs/README.md) | All 14 repair scripts: what each fixes, usage notes |

### Reference

| Document | Description |
| --- | --- |
| [`rsc/snippets.md`](rsc/snippets.md) | jq recipes: redaction, summarisation, frequency analysis, export inspection |
| [`src/test/xref.sh`](src/test/xref.sh) | Cross-reference audit: scans all source files for inter-file links, flags missing targets and unreferenced files |

### Tool context

These document `~/.claude/` — the Claude Code local state — rather than the project itself.

| Document | Description |
| --- | --- |
| [`doc/tool-context/claude-home-directory.md`](doc/tool-context/claude-home-directory.md) | Directory-by-directory reference for `~/.claude/` and `~/.claude.json` |
| [`doc/tool-context/investigation-methodology.md`](doc/tool-context/investigation-methodology.md) | How to reverse-engineer an undocumented directory; reusable beyond this project |
