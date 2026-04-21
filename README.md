# Instructions

- Prepare new data
  - Ask to "Export ('All') data" from <https://claude.ai/settings/data-privacy-controls>
  - Click on 24-hour emailed "Download Data" link (like <https://claude.ai/export/0fc4c1e0-4719-4e10-997a-697bf05599af/download/cdb658167a0d6dd4a2ffe829aeea9d15>)
  - Move downloaded folder (like `data-*`) from `Downloads` into the `data-exports` sibling directory of this (current) directory.
  - `source ~/.zprofile` (to get `ANTHROPIC_API_KEY` into `env` for table inference by Claude)

```bash
./RUNME.sh
```

## What that does

- Validate the data
  - `./src/main/validate.sh --data-root ../data-exports`
- Address any errors by updating/retesting the schemas (in `./rsc`) and tooling (in `./src`) as needed.
- Extract files and heredocs
  - `./src/main/extract_files.sh --data-root ../data-exports`
  - `./src/main/extract_heredocs.sh --data-root ../data-exports`
- Present the data
  - `./src/main/infer_tables.sh --data-root ../data-exports`
  - NB the above call requires an Anthropic API key and costs money.
  - `./src/main/present.sh --data-root ../data-exports`

---

## To be tested

- Process `conversations.json` using `src/main/test/gen_model_candidate.py` (according to the instructions in its header comment).
  - `mkdir ./gen/data-*/model`
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
