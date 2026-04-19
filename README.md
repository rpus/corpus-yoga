# Instructions

```bash
rm -rf ./gen

./src/main/validate.sh --data-root ../exported-data

# source ~/.zprofile 
./src/main/infer_tables.sh --data-root ../exported-data

./src/main/present.sh --data-root ../exported-data
```

- Prepare new data
  - Ask to "Export ('All') data" from <https://claude.ai/settings/data-privacy-controls>
  - Click on 24-hour emailed "Download Data" link (like <https://claude.ai/export/0fc4c1e0-4719-4e10-997a-697bf05599af/download/cdb658167a0d6dd4a2ffe829aeea9d15>)
  - Move downloaded folder (like `data-*`) from `Downloads` to the `exported-data` sibling directory of this (current) directory.
  - Format (with-two-space indentation) and re-save the (four, `.json`) files in `data-*`.
- Validate the data
  - `./src/main/validate.sh --data-root ../exported-data`
  - Address any errors by updating/retesting the schemas (in `./rsc`) and tooling (in `./src`) as needed.
- Present the data
  - `source ~/.zprofile # to get Anthropic API key into env for table inference by Claude`
  - `./src/main/infer_tables.sh --data-root ../exported-data`
  - `./src/main/present.sh --data-root ../exported-data`

---

## To be tested

- Process `conversations.json` using `src/main/gen_model_candidate.py` (according to the instructions in its header comment).
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
