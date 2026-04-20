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
