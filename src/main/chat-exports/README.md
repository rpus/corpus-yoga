# chat-exports

Pipeline for processing Claude.ai bulk data exports: validates, extracts recovered files, infers semantic structure, and assembles an HTML dashboard.

---

## Usage

Each script accepts a single export or all exports (**ONE OF**):

```bash
src/main/chat-exports/RUNME.sh --chat-export  ext/chat-exports/data-<...>
src/main/chat-exports/RUNME.sh --chat-exports ext/chat-exports
```

`RUNME.sh` runs all stages in order. Each stage can also be run independently with the same `--chat-export` / `--chat-exports` flags.

---

## Stages

| # | Script | What it does | Output |
| --- | --- | --- | --- |
| 1 | `validate.sh` | Validates each `.json` against all schema versions in `rsc/schema/chat-exports/`. On failure, prints the failing path, schema fragment, and every offending instance. | `gen/chat-exports/<export>/validation/` |
| 2 | `extract_files.sh` | Recovers files written via `create_file` tool calls. Strips container path prefixes; last write wins. | `gen/chat-exports/<export>/extracted_files/` |
| 3 | `extract_heredocs.sh` | Recovers files written via bash heredocs. Classifies by destination: `outputs/` (`/mnt/user-data/outputs/`) and `working/` (`/home/claude/`). | `gen/chat-exports/<export>/extracted_heredocs/` |
| 4 | `audit_files.sh` | Full-outer-join across all file sources (tooltip, extract_files, extract_heredocs, downloaded). Runs SQL queries and reports gaps. | `gen/chat-exports/<export>/audit_queries/` |
| 5 | `infer_tables.sh` | *(optional — requires `ANTHROPIC_API_KEY`)* Calls the Claude API to infer categories, chat-category assignments, and weighted key concepts. | `gen/chat-exports/<export>/inferred/` |
| 6 | `present.sh` | Assembles all data into a self-contained HTML dashboard. | `gen/chat-exports/<export>/presentation/index.html` |

---

## Files

### Pipeline scripts

| File | What it does |
| --- | --- |
| `RUNME.sh` | Runs all six stages in order |
| `validate.sh` | Per-export JSON Schema validation; detailed failure diagnostics |
| `extract_files.sh` / `extract_files.py` | Recovers files from `create_file` tool calls |
| `extract_heredocs.sh` / `extract_heredocs.py` | Recovers files from bash heredocs |
| `audit_files.sh` / `audit_files.py` | Full-outer-join file audit; writes `files_audit.csv` |
| `infer_tables.sh` | Claude API inference: categories, chat assignments, semantic concepts |
| `present.sh` | Assembles HTML dashboard from `rsc/index.html` template |

### Support scripts (called by pipeline scripts, not directly)

| File | What it does |
| --- | --- |
| `query_files.py` | Runs SQL queries against the audit CSV |
| `files_from_downloaded.py` | Produces the data-files tooltip table from `lib/artifacts/downloaded/` |
| `check_harvested.py` | Reports tool-result file references not recovered by extraction |
| `word_freq_literal.py` | Literal word frequency counts from `conversations.json` |
| `format_table.py` | Reads JSON, writes column-aligned table JSON |
| `schema_path.py` / `schema_fragment.py` / `schema_occurrences.py` | Validation failure diagnostics: schema path lookup, fragment extraction, occurrence search |
