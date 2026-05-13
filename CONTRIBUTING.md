# CONTRIBUTING

This file is the authoritative substitute for the project memory stored at
`~/.claude/projects/-Users-*-claude-export-yoga/memory/MEMORY.md`. Do not modify that file or directory; edit this file instead as needed.

For the full human-facing how-to, prerequisites, and documentation index see
[`README.md`](README.md) (for the as-is state) and [`TODO.md`](TODO.md) (for the to-be state). The `doc/` directory contains deep-dives on each pipeline
and schema.

---

## What this repo does

Processes Claude.ai chat exports and Claude Code CLI session transcripts: validates
them, recovers files Claude created during conversations, infers semantic structure,
and renders an interactive HTML dashboard.

---

## Critical naming convention

**`conversations`** = the data format and schema name (`conversations.json`,
`rsc/schema/chat-exports/conversations/`).

**`chat-exports`** = the pipeline that processes claude.ai exports
(`src/main/chat-exports/`, `../chat-exports/`).

These are kept strictly distinct throughout. Do not conflate them.

---

## Inputs (in workspace, but not in repo)

- `../chat-exports/` — claude.ai bulk exports (contains `conversations.json` etc.)
- `../code-projects/` — symlink to `~/.claude/projects/` for CLI `.jsonl` sessions
- `../browser-captures/` — per-conversation browser captures (markdown + API JSON)

---

## Pipelines

```bash
src/main/chat-exports/RUNME.sh  --chat-exports  ../chat-exports
src/main/code-projects/RUNME.sh --code-projects ../code-projects
```

---

## Key invariants

- Run `src/test/pre_commit.sh` before and after any change. All checks must pass. Expected score is tracked in [`src/test/pre_commit_expected_score`](src/test/pre_commit_expected_score) — update it when check counts change. Output is logged to [`src/test/pre_commit.log`](src/test/pre_commit.log) — commit it so diffs show what shifted. **After each run, read the result via `git diff src/test/pre_commit.log` — not by scanning live output with tail or grep.**
- Run `src/test/xref.sh` after structural changes to catch stale references. Expected counts are tracked in [`src/test/xref_expected_score`](src/test/xref_expected_score) — update it when reference counts change. Output is [`src/test/xref.csv`](src/test/xref.csv) — commit it so diffs show what references changed.
- `git clean -fdX; git clean -fdxn` after a full run — the output should be fully accounted for.
- `rsc/artifacts/downloaded/` is ground truth — never edit files in place. It is already excluded from `xref.py` scanning (`rsc/artifacts/` is in `SKIP_DIRS` and `repo_files()` has an explicit additional check); bulk operations (`find`/`sed`/etc.) must exclude it too, alongside `gen/` and `.git/`.

---

## Venv

`src/activate_venv.sh` is the single canonical activator. Path: `~/venvs/general`
(overridable via `$VENV`). Sets `trap deactivate EXIT` — callers never deactivate
manually. Dependencies: `requirements.txt`.

---

## Schema directories

Grouped by pipeline, named after the data format within each:
`rsc/schema/chat-exports/conversations/` (currently v1–v7), `rsc/schema/code-projects/session/` (currently v1–v3),
`rsc/schema/browser-captures/apiConversation/` (currently v1).

`rsc/schema/browser-captures/apiConversation/v1.json` validates live claude.ai API responses (`ApiConversation`
and related subtypes). No existing `conversations/` definitions modified.
`ApiConversation` validated against 55 live API responses (all pass).

---

## Browser captures (pre-processing)

Two modes — same JS ([`browser-chat-capture.js`](src/main/browser-captures/browser-chat-capture.js)), different scope and destination.
See [`src/main/browser-captures/README.md`](src/main/browser-captures/README.md) for setup and troubleshooting.

**Shortcut mode** (standalone, no pipeline knowledge needed):

```bash
# Shortcuts app action — works on claude.ai/chat/* (single) or claude.ai/recents (all):
caffeinate -dim osascript "$HOME/dev/Anthropic/claude-export-yoga/src/main/browser-captures/export.applescript"
```

Output goes to `~/Downloads/` as `{name}.md` + `{name}.log` + `{uuid}.json` per conversation.
Entry points: [`export.applescript`](src/main/browser-captures/export.applescript) (dispatcher),
[`export-conversation.applescript`](src/main/browser-captures/export-conversation.applescript),
[`export-all-conversations.applescript`](src/main/browser-captures/export-all-conversations.applescript).

**Pipeline mode** (scope-constrained to a bulk export):

```bash
src/main/browser-captures/safari_capture.sh --chat-export ../chat-exports/data-<...>
```

Requires Safari open and logged into claude.ai. Output goes to
`../browser-captures/<export-name>/<uuid>/`.

To fetch live API JSON for existing captures that don't have it:

```bash
src/main/browser-captures/safari_fetch_api_json.sh --browser-capture ../browser-captures/data-<...>
```

Saves `{title}.json` alongside each `.md` and `.log`.

To validate the captured API JSON against `rsc/schema/browser-captures/apiConversation/v1.json`:

```bash
src/main/browser-captures/RUNME.sh --browser-capture ../browser-captures/data-<...>
```

---

## Design principle: look the same if and only if the same

Things that are functionally equivalent should look structurally identical; things that differ should
look different. Unexplained asymmetry is always a signal — either the asymmetry is
meaningful (document it) or it is accidental (fix it). This applies at every level:
schema definitions, function names, section headers, variable names, file layout,
flag names, and documentation structure.
Structural symmetry, meanwhile, allows for easy factoring of commonality.

---

## Project

Key points:

- `conversations` = data format/schema; `chat-exports` = pipeline. Never conflate.
- Three pipelines: `chat-exports`, `code-projects`, `browser-captures` — see `doc/pipeline-model.md`
- Invariants: see Key invariants section above; `git clean -fdX; git clean -fdxn`
- Venv: `src/activate_venv.sh`, overridable via `$VENV`, trap handles deactivation
- Schemas: `rsc/schema/chat-exports/conversations/` (v1–v7), `rsc/schema/code-projects/session/` (v1–v3), `rsc/schema/browser-captures/apiConversation/` (v1)
- `rsc/schema/model_join.csv` — unified 4-way join: conversations ↔ session ↔ apiConversation ↔ MCP
- `src/test/gen_changelog_matrix.py` — generates CHANGELOG rows from gen/ logs for any pipeline
- Validation matrix driven by CHANGELOG.md files (not hardcoded constants) via `_parse_changelog_matrix()`
