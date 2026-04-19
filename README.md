# Instructions

```bash
rm -rf ./gen

./src/main/validate.sh --data-root ../exported-data

# source ~/.zprofile 
./src/main/infer_tables.sh --data-root ../exported-data

./src/main/present.sh --data-root ../exported-data
```

- Fetch new data
  - `mkdir ./gen/data-*`
  - Ask to "Export ('All') data" from <https://claude.ai/settings/data-privacy-controls>
  - Click on 24-hour emailed "Download Data" link (like <https://claude.ai/export/0fc4c1e0-4719-4e10-997a-697bf05599af/download/cdb658167a0d6dd4a2ffe829aeea9d15>)
  - Move downloaded folder (like `data-2026-04-05-10-33-48-batch-0000`) from `Downloads` to the `exported-data` sibling directory of this (current) directory.
- Validate the data
  - `mkdir ./gen/data-*/validation`
  - Format (with-two-space indentation) and re-save the (four, `.json`) files in `data-`.
  - Validate `*.json` using `src/main/validate.sh` (according to the instructions in its header comment).
  - Address any errors by updating/retesting the schemas (improving the tooling as needed).
- Present the data
  - `src/main/present.sh --data-root ../exported-data`

---

```bash
mkdir ./gen/data-*/model
mkdir ./gen/data-*/redacted
mkdir ./gen/data-*/summarised
mkdir ./gen/data-*/validation
```

## To test

- Process `conversations.json` using `src/main/gen_model_candidate.py` (according to the instructions in its header comment).
- Process `conversations.json` using the redaction snippet in `rsc/snippets.md`.
- Process `conversations.json` using the summarisation snippet in `rsc/snippets.md`.

## To implement

- Make a `chat_links.json` file to hold public viewing links for each chat.
- Make a `summaries.md` file (using claude-chat-exporter).
- Make a `memory.md`.
- Make an output/files directory.
