# README

This repo wrangles Claude data exports.

## Prerequsites

- python

## How to use

- Prepare new data
  - Ask to "Export ('All') data" from <https://claude.ai/settings/data-privacy-controls>
  - Click on 24-hour emailed "Download Data" link (like <https://claude.ai/export/0fc4c1e0-4719-4e10-997a-697bf05599af/download/cdb658167a0d6dd4a2ffe829aeea9d15>)
  - Move downloaded folder (like `data-*`) from `Downloads` into the `data-exports` sibling directory of this (current) directory.
  - `source ~/.zprofile` (to get `ANTHROPIC_API_KEY` into `env` for table inference by Claude)

```bash
./RUNME.sh
./src/test/audit_files.sh
./src/test/xref.sh
./RUNME-code-sessions.sh
# ./src/test/pre_commit.sh
git clean -fdX; git clean -fdxn
```

## What that does

- Validate the data
  - `./src/main/validate.sh --data-root ../data-exports`
- Address any errors by updating/retesting the schemas (in `./rsc/schema`) and tooling (in `./src/main`) as needed.
- Extract files and heredocs
  - `./src/main/extract_files.sh --data-root ../data-exports`
  - `./src/main/extract_heredocs.sh --data-root ../data-exports`
- Present the data
  - `./src/main/infer_tables.sh --data-root ../data-exports`
  - NB the above call requires an Anthropic API key and costs money.
  - `./src/main/present.sh --data-root ../data-exports`

---

## Schema maintenance

When the conversations schema changes, regenerate the model candidates and review `rsc/model.json`:

```bash
./src/test/gen_model.sh
```

When a new Claude Code session appears in `../code-sessions/` or `rsc/schema/claude-code-sessions/v1.json` changes, follow the validation loop in `rsc/schema/claude-code-sessions/workflow.md`. In brief:

```bash
./RUNME-code-sessions.sh
# if a record fails:
python src/test/debug_code_session_record.py gen/code-sessions/{project}/{session}/session.json
python src/test/pre_commit.py
```

---

## To be tested

- Process `conversations.json` using the redaction snippet in `rsc/snippets.md`.
  - `mkdir ./gen/data-*/redacted`
- Process `conversations.json` using the summarisation snippet in `rsc/snippets.md`.
  - `mkdir ./gen/data-*/summarised`

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
| [`doc/project-overview.md`](doc/project-overview.md) | Architecture: pipeline stages, artifact recovery, all schemas, output structure, provenance |
| [`doc/conversations-schema.md`](doc/conversations-schema.md) | Deep-dive on `rsc/schema/conversations/`: versioning, format comparison, workflow summary, MCP correspondence |
| [`doc/code-sessions-schema.md`](doc/code-sessions-schema.md) | Reference for `rsc/schema/claude-code-sessions/`: the nine record types, turn envelope, content blocks, MCP mapping |
| [`doc/code-sessions-research.md`](doc/code-sessions-research.md) | How the CLI session format was reverse-engineered; `../code-sessions/` setup procedure |
| [`RUNME-code-sessions.sh`](RUNME-code-sessions.sh) | Entry point: convert `.jsonl` sessions to JSON arrays and validate against the schema |
| [`src/test/survey_code_session.py`](src/test/survey_code_session.py) | Survey record types and field structure of session files (used during schema development) |
| [`src/test/debug_code_session_record.py`](src/test/debug_code_session_record.py) | Diagnose why a specific record fails validation: tests each `Record.oneOf` branch and drills into the matching subtype |

### Schema

| Document | Description |
| --- | --- |
| [`rsc/schema/conversations/principles.md`](rsc/schema/conversations/principles.md) | Every design rule for the conversations schema, with diagnostic/repair scripts and inline snippets |
| [`rsc/schema/conversations/workflow.md`](rsc/schema/conversations/workflow.md) | 11-step loop for incorporating new exports and making schema changes |
| [`rsc/schema/conversations/CHANGELOG.md`](rsc/schema/conversations/CHANGELOG.md) | Version history and export compatibility matrix |
| [`rsc/schema/conversations/README.md`](rsc/schema/conversations/README.md) | Format comparison: CLI `.jsonl` vs claude.ai export |
| [`rsc/schema/claude-code-sessions/README.md`](rsc/schema/claude-code-sessions/README.md) | CLI sessions schema at a glance: record types, content blocks, MCP mapping table |
| [`rsc/schema/claude-code-sessions/principles.md`](rsc/schema/claude-code-sessions/principles.md) | Schema design principles: defers to conversations/principles.md; documents justified deviations |
| [`rsc/schema/claude-code-sessions/workflow.md`](rsc/schema/claude-code-sessions/workflow.md) | Validation loop, `cli_join.csv` maintenance, versioning, real-time vs snapshot lifecycle |
| [`rsc/schema/claude-code-sessions/CHANGELOG.md`](rsc/schema/claude-code-sessions/CHANGELOG.md) | Version history and session coverage matrix |
| [`rsc/schema/claude-code-sessions/cli_join.csv`](rsc/schema/claude-code-sessions/cli_join.csv) | Field-level correspondence table: CLI sessions ↔ conversations export ↔ MCP protocol |

### Reference

| Document | Description |
| --- | --- |
| [`rsc/snippets.md`](rsc/snippets.md) | jq recipes: redaction, summarisation, frequency analysis, export inspection |

### Tool context

These document `~/.claude/` — the Claude Code local state — rather than the project itself.

| Document | Description |
| --- | --- |
| [`doc/claude-home-directory.md`](doc/claude-home-directory.md) | Directory-by-directory reference for `~/.claude/` and `~/.claude.json` |
| [`doc/investigation-methodology.md`](doc/investigation-methodology.md) | How to reverse-engineer an undocumented directory; reusable beyond this project |

---

## Notes on provenance

- `rsc/schema/conversations/principles.md`
  - Originated in conversation 15 ("Accessing files from previous chats"). Downloaded version is v1.2; repo is v1.3 (one minor revision ahead).
- `rsc/schema/conversations/workflow.md`
  - Originated in conversation 15. Downloaded version is v1.0; repo is v1.3.
- `src/main/validate.py`
  - Originated in conversation 30 ("JSON Schema and jq fundamentals"). Repo version substantially extended: added JSON Pointer fragment support (RFC 6901), `$ref` resolution via the `referencing` library, and removed the earlier custom discriminator-based `oneOf` error formatting.
- `src/main/word_freq_literal.py`
  - Originated in conversation 30. Repo version is identical except for the addition of a `#!/usr/bin/env python` shebang.
- `src/test/gen_model_candidate.py`
  - Originated in conversation 15. Repo version accepts the schema path as an explicit second argument rather than deriving it from the name, and uses `removesuffix` in place of manual string slicing.
- `src/test/pre_commit.py`
  - Originated in conversation 15. Repo version heavily extended: added versioned schema support (`v1`–`v4`) and an `EXPECTED_PASS` matrix of (export, schema-version) pairs, and updated required-files and validation sections to match the evolved repo layout.
