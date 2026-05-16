# doc/

Architecture reference for this repo. The root `README.md` covers usage; this document covers how everything fits together.

---

## Inputs

### Claude.ai exports (`ext/chat-exports/`)

Requested from Settings → Privacy → Export Data on claude.ai. Each export is a directory named by account UUID and timestamp:

```text
data-{account-uuid}-{unix-timestamp}-{hash}-batch-0000/
├── conversations.json    ← all conversations (primary input)
├── memories.json         ← stored user memories
├── projects.json         ← project metadata
└── users.json            ← account info
```

The `CHANGELOG.md` in `rsc/schema/chat-exports/conversations/` tracks which exports have been processed and which schema version each passes.

### Claude Code CLI sessions (`ext/code-projects/`)

Session transcripts written by Claude Code to `~/.claude/projects/{project}/{session}.jsonl`.
`ext/code-projects/` is a symlink directly to `~/.claude/projects/`. One-time setup:

```bash
ln -sfn ~/.claude/projects ext/code-projects
```

See `rsc/schema/code-projects/session/research.md` for setup and format documentation.

### Browser captures (`ext/browser-captures/`)

Per-conversation API JSON files captured from the live claude.ai API via Safari automation. See `rsc/schema/browser-captures/apiConversation/research.md` for how the endpoint was discovered and how captures are taken.

---

## Source layout

`src/main/` mirrors `gen/` — each subdirectory corresponds to a pipeline or shared utility:

| Directory | Role |
| --- | --- |
| [`src/main/chat-exports/`](src/main/chat-exports/README.md) | Chat-exports pipeline scripts |
| [`src/main/code-projects/`](src/main/code-projects/README.md) | Code-projects pipeline scripts |
| [`src/main/browser-captures/`](src/main/browser-captures/README.md) | Browser-captures pipeline scripts |
| [`src/main/model/`](src/main/model/README.md) | Cross-pipeline schema model generation and markdown viewer |
| `src/main/validate.py` | Shared JSON Schema validator |
| `src/main/validate_versions.py` | Shared per-version validation loop |
| `src/main/schema_recommendations.py` | Shared post-validation schema quality hints |

`src/test/` contains the pre-commit suite, xref tool, diagnostic and repair scripts, and pipeline-specific debug tools.

---

## Pipelines

### chat-exports

`src/main/chat-exports/RUNME.sh` orchestrates six stages in order. Each can also be run independently.

1. **`validate.sh`** — validates each `.json` against all schema versions in `rsc/schema/chat-exports/`. On failure prints the failing path, schema fragment, and every offending instance.
2. **`extract_files.sh`** — extracts files written via `create_file` tool calls. Strips container path prefixes; last write wins.
3. **`extract_heredocs.sh`** — extracts files written via bash heredocs. Classifies by destination: `outputs/` (`/mnt/user-data/outputs/`) and `working/` (`/home/claude/`). Produces diffs against downloaded versions.
4. **`audit_files.sh`** — cross-references all file sources (tooltip, extract_files, extract_heredocs, downloaded) and runs SQL queries across them.
5. **`infer_tables.sh`** *(optional, requires `ANTHROPIC_API_KEY`)* — calls the Claude API to infer categories, chat-category assignments, and weighted key concepts.
6. **`present.sh`** — assembles all data sources into a self-contained HTML dashboard.

### code-projects

`src/main/code-projects/RUNME.sh` converts each `.jsonl` session to a JSON array and validates it against all versions of `rsc/schema/code-projects/session/`.

### browser-captures

`src/main/browser-captures/RUNME.sh` validates each captured API JSON file against all versions of `rsc/schema/browser-captures/apiConversation/`.

---

## Artifact recovery

Files Claude creates during conversations are recovered via two complementary paths:

```text
lib/artifacts/
├── downloaded/          ← manually curated; ground truth
│   └── <chat>_<slug>/
│       └── <path>
├── extracted_files/     ← auto-recovered via create_file tool calls
└── extracted_heredocs/  ← auto-recovered via bash heredocs
```

`lib/artifacts/downloaded/` is the source of truth. `audit_files.sh` cross-references all sources and reports gaps. `check_harvested.py` (called from `present.sh`) reports tool-result references that were not recovered by either extraction path.

---

## Schemas

Six JSON Schemas (draft-4) in `rsc/schema/`, grouped by pipeline:

| Schema | Validates |
| --- | --- |
| `rsc/schema/chat-exports/conversations/v7.json` | `conversations.json` — full conversation history (versioned) |
| `rsc/schema/chat-exports/memories/v1.json` | `memories.json` — stored user memories |
| `rsc/schema/chat-exports/projects/v1.json` | `projects.json` — project metadata |
| `rsc/schema/chat-exports/users/v1.json` | `users.json` — account information |
| `rsc/schema/code-projects/session/v2.json` | `{session}.jsonl` → JSON array — Claude Code CLI sessions |
| `rsc/schema/browser-captures/apiConversation/v1.json` | `{uuid}.json` — live claude.ai API conversation response |

Supporting files (cross-pipeline, at `rsc/schema/` root):

| File | Purpose |
| --- | --- |
| `rsc/schema/_reference/mcp.json` | MCP protocol type definitions; used by `rsc/schema/model_join.csv` for field-level comparison |
| [`rsc/schema/documenter.json`](../rsc/schema/documenter.json) | VS Code tooltip wrapper; enables schema-aware editing of data files |
| `rsc/schema/model.json` | JSON Schema for the cross-pipeline type reference; the reference data is inlined in its `default` field |
| `rsc/schema/model_join.csv` | Unified four-way field correspondence table: conversations ↔ session ↔ apiConversation ↔ MCP |

---

## Output

All generated output lives under `gen/`, which is gitignored.

### `gen/chat-exports/<export>/`

```text
├── validation/{schema}/v{N}.log
├── extracted_files/<chat>_<slug>/<path>
├── extracted_heredocs/<chat>_<slug>/{outputs,working}/<path>
├── audit_queries/files_audit.csv  (+ joined table and query results)
├── inferred/                      (only if --pay-for-inference)
│   ├── data-categories.json
│   ├── data-chat-categories.json
│   └── data-semantic.json
└── presentation/
    ├── index.html                 ← self-contained dashboard
    ├── data-chats.json
    ├── data-spans.json
    ├── data-files.json
    ├── data-literal.json
    ├── data-local-resources.json
    ├── data-categories.json
    ├── data-chat-categories.json
    └── data-semantic.json
```

### `gen/code-projects/{project}/{session}/`

```text
├── session.json                   # JSONL converted to JSON array
└── validation/session/v{N}.log   # one log per schema version
```

### `gen/browser-captures/{batch}/{uuid}/`

```text
└── validation/apiConversation/v{N}.log   # one log per schema version
```

### `gen/model/{schema}/`

```text
└── v{N}.json   # candidate definition catalogue for rsc/schema/model.json
```

---

## Provenance

Several scripts originated in conversations visible in the exports themselves:

| File | Origin |
| --- | --- |
| `rsc/schema/chat-exports/conversations/principles.md` | Conversation 15 ("Accessing files from previous chats"), v1.2 → extended to v1.3 in repo |
| `rsc/schema/chat-exports/conversations/workflow.md` | Conversation 15, v1.0 → extended to v1.3 in repo |
| `src/main/validate.py` | Conversation 30 ("JSON Schema and jq fundamentals"), extended with JSON Pointer / `$ref` resolution |
| `src/main/chat-exports/word_freq_literal.py` | Conversation 30, identical except shebang |
| `src/main/model/gen_model_candidate.py` | Conversation 15, minor interface changes |

---

## Sub-documents

### chat-exports docs

#### [`rsc/schema/chat-exports/conversations/conversations-schema.md`](rsc/schema/chat-exports/conversations/conversations-schema.md)

Deep-dive on `rsc/schema/chat-exports/conversations/`: versioned JSON Schemas, two-format distinction, schema development workflow, MCP field-level correspondence table.

---

### browser-captures docs

#### [`rsc/schema/browser-captures/apiConversation/api-conversation-schema.md`](rsc/schema/browser-captures/apiConversation/api-conversation-schema.md)

Reference for `rsc/schema/browser-captures/apiConversation/`: structure, differences from bulk export, tool blocks.

#### [`rsc/schema/browser-captures/apiConversation/research.md`](rsc/schema/browser-captures/apiConversation/research.md)

How the live API endpoint was discovered and captured; capture setup and output structure.

---

### code-projects docs

#### [`rsc/schema/code-projects/session/session-schema.md`](rsc/schema/code-projects/session/session-schema.md)

Reference for `rsc/schema/code-projects/session/`: nine record types, turn envelope fields, content block types, MCP field mapping.

#### [`rsc/schema/code-projects/session/research.md`](rsc/schema/code-projects/session/research.md)

How the CLI session format was reverse-engineered; `ext/code-projects/` setup procedure.

#### [`rsc/schema/code-projects/session/claude-home-directory.md`](rsc/schema/code-projects/session/claude-home-directory.md)

Directory-by-directory reference for `~/.claude/` and `~/.claude.json`.
