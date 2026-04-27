# Project Overview

This repo processes Claude.ai conversation exports: it validates them, recovers files that
Claude created during conversations, infers semantic structure via the Claude API, and
renders everything as an interactive HTML dashboard.

The root `README.md` covers usage; this document covers architecture.

---

## Inputs

### Claude.ai exports (`../data-exports/`)

Requested from Settings → Privacy → Export Data on claude.ai. Each export is a
directory named by account UUID and timestamp:

```text
data-{account-uuid}-{unix-timestamp}-{hash}-batch-0000/
├── conversations.json    ← all conversations (primary input)
├── memories.json         ← stored user memories
├── projects.json         ← project metadata
└── users.json            ← account info
```

These live in `../data-exports/` (a sibling directory, not in this repo). The `CHANGELOG.md`
in `rsc/schema/conversations/` tracks which exports have been processed and which schema
version each passes.

Earlier exports used a simpler date-only naming: `data-2026-03-19-22-47-05-batch-0000`.

### Claude Code CLI sessions (`../code-sessions/`)

Session transcripts written by Claude Code to `~/.claude/projects/{project}/{session}.jsonl`.
The `../code-sessions/` sibling directory contains named symlinks into `~/.claude/projects/`
so the pipeline can reference them without knowing the opaque path naming convention.

```bash
# To add sessions for another repo:
ln -sfn ~/.claude/projects/-Users-{user}-{path...} ../code-sessions/my-project-name
```

See `doc/code-sessions-research.md` for the full setup procedure and format documentation.

---

## Pipeline

`RUNME.sh` orchestrates four stages in order. Each stage can also be run independently.

### 1. `src/main/validate.sh` → `validate.py`

Validates `conversations.json` against the versioned JSON Schema in
`rsc/schema/conversations/` (currently `rsc/schema/conversations/v6.json`). On failure,
prints the failing path, the relevant schema fragment, every instance of the offending
value in the export, and a suggested remediation command. On success, runs
`schema_recommendations.py` to suggest possible schema improvements.

When the export fails validation, the schema is updated (following the workflow in
`rsc/schema/conversations/workflow.md`) until it passes.

Output: `gen/data-exports/{export-name}/validation/conversations/` — one `.log` per schema version

### 2. `src/main/extract_files.sh` → `extract_files.py`

Extracts files that Claude wrote via `create_file` tool calls. These are explicit JSON
records in the conversation — structured and reliable.

- Strips container path prefixes (`/home/claude/`, `/mnt/user-data/outputs/`)
- Rejects path traversal and absolute paths after prefix stripping
- Last write wins when Claude revised a file multiple times
- Cross-references with `rsc/artifacts/downloaded/` and copies new finds there

Output: `gen/data-exports/{export-name}/extracted_files/` — one subdirectory per conversation

### 3. `src/main/extract_heredocs.sh` → `extract_heredocs.py`

Extracts files that Claude wrote via bash heredocs — `cat > /path << 'EOF' ... EOF`
patterns inside `bash_tool` commands. These require regex reconstruction from raw text.

Classifies by destination prefix:

| Prefix | Bucket |
| --- | --- |
| `/mnt/user-data/outputs/` | `outputs/` |
| `/home/claude/` | `working/` |

Produces unified diffs for files that diverge from the downloaded version. Files with
only whitespace differences are noted but not treated as changes.

Output: `gen/data-exports/{export-name}/extracted_heredocs/` — one subdirectory per conversation, each with `outputs/` and `working/` buckets

### 4. `src/main/infer_tables.sh` *(optional — requires `ANTHROPIC_API_KEY`, costs money)*

Calls the Claude API three times to infer semantic structure:

1. **data-categories** — 6–10 topic categories for this export, each with an HSV hue value for visualisation
2. **data-chat-categories** — assigns each conversation to one category
3. **data-semantic** — weighted key concepts (salience, not raw frequency)

Uses `claude-sonnet-4-6` with `max_tokens: 1024`. Skipped if `--pay-for-inference` is not
passed to `RUNME.sh`.

Output: three `.json` tables under `gen/data-exports/{export-name}/inferred/`

### 5. `src/main/present.sh`

Assembles all data sources into the interactive HTML dashboard. Runs several transforms:

- **data-chats** (jq): conversation index, name, last-active timestamp
- **data-spans** (jq): consecutive same-chat message runs for the timeline
- **data-literal** (Python): word frequency for human, assistant, and combined (top 120 each; 230-word stoplist)
- **data-files** (Python): canonical file manifest from `rsc/artifacts/downloaded/`
- **data-local-resources** (jq): raw tool-result file references for cross-checking
- **check_harvested.py**: cross-references tool-result records against extracted files; reports unrecovered artifacts
- Claude-inferred tables (injected if present, empty stubs if not)

Injects all datasets into the `rsc/index.html` template via `<!-- key.json:begin/end -->`
markers or `<script id="key">` tags, producing a self-contained HTML file.

Output: a self-contained `index.html` dashboard plus `data-*.json` datasets under `gen/data-exports/{export-name}/presentation/`

---

## Artifact recovery

Files that Claude creates during conversations can be recovered via two paths. Both are
run against every export; their output is cross-referenced.

```text
rsc/artifacts/
├── downloaded/          ← manually curated; ground truth
│   └── <chat>_<slug>/  ← mirrors the chat index used in gen/
│       └── <path>
├── extracted_files/     ← auto-recovered via create_file tool calls
└── extracted_heredocs/  ← auto-recovered via bash heredocs
```

`rsc/artifacts/downloaded/` is the source of truth. Files found by extraction that are not
already there are copied in for manual review. `check_harvested.py` reports the gaps:
files referenced in tool results that were not recovered by either extraction path.

---

## Schemas

Four JSON Schemas (draft-4) in `rsc/schema/`, one per export file type:

| Schema | Validates |
| --- | --- |
| `rsc/schema/conversations/v6.json` | `conversations.json` — full conversation history (claude.ai export; versioned) |
| `rsc/schema/memories/memories.json` | `memories.json` — stored user memories |
| `rsc/schema/projects/projects.json` | `projects.json` — project metadata |
| `rsc/schema/users/users.json` | `users.json` — account information |
| `rsc/schema/claude-code-sessions/v1.json` | `{session}.jsonl` → JSON array — Claude Code CLI sessions |

Supporting files:

| File | Purpose |
| --- | --- |
| `mcp.json` | MCP protocol type definitions; used by `mcp_join.csv` for field-level comparison |
| `data-table.json` | Generic columnar table format; used by inferred and computed datasets |
| `documenter.json` | VS Code tooltip wrapper; enables schema-aware editing of data files |
| `model.json` | Cross-schema type reference table |
| `json-schema_draft-04.json` | The JSON Schema meta-schema itself |

The conversations schema has the most elaborate maintenance apparatus (versioned files,
`principles.md`, `workflow.md`, diagnostic suite). See
[`doc/conversations-schema.md`](conversations-schema.md) for details.

---

## Output

All generated output lives under `gen/`, which is gitignored.

### Data exports (`gen/data-exports/`)

For each processed claude.ai export:

```text
gen/data-exports/<export>/
├── validation/
│   └── conversations/v{N}.log
├── extracted_files/
│   └── <chat>_<slug>/<path>
├── extracted_heredocs/
│   └── <chat>_<slug>/{outputs,working}/<path>
├── inferred/                    ← only if --pay-for-inference
│   ├── data-categories.json
│   ├── data-chat-categories.json
│   ├── data-semantic.json
│   └── infer.log
└── presentation/
    ├── index.html               ← the dashboard
    ├── present.log
    ├── data-chats.json
    ├── data-spans.json
    ├── data-files.json
    ├── data-literal.json
    ├── data-local-resources.json
    ├── data-categories.json
    ├── data-chat-categories.json
    └── data-semantic.json
```

### Code sessions (gen/code-sessions/)

For each processed CLI session project (currently a placeholder — pipeline not yet
implemented), output would go under gen/code-sessions/{project-name}/validation/.

The dashboard `index.html` is self-contained and can be opened directly in a browser.

---

## Provenance

Several scripts in this repo originated in conversations visible in the exports themselves
— a recursive quality, since the schema describes the conversations in which it was built:

| File | Origin |
| --- | --- |
| `rsc/schema/conversations/principles.md` | Conversation 15 ("Accessing files from previous chats"), v1.2 → extended to v1.3 in repo |
| `rsc/schema/conversations/workflow.md` | Conversation 15, v1.0 → extended to v1.3 in repo |
| `src/main/validate.py` | Conversation 30 ("JSON Schema and jq fundamentals"), extended with JSON Pointer / `$ref` resolution |
| `src/main/word_freq_literal.py` | Conversation 30, identical except shebang |
| `src/test/gen_model_candidate.py` | Conversation 15, minor interface changes |
| `src/test/pre_commit.py` | Conversation 15, heavily extended for multi-version schema support |

The `rsc/artifacts/downloaded/` directory contains files downloaded from those same
conversations.
