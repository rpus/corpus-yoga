# CLAUDE.md

This file is the authoritative substitute for the project memory stored at
`~/.claude/projects/-Users-*-claude-export-yoga/memory/MEMORY.md`. Do not modify that file or directory; edit this file instead as needed.

For the full human-facing how-to, prerequisites, and documentation index see
[`README.md`](README.md). The `doc/` directory contains deep-dives on each pipeline
and schema.

---

## What this repo does

Processes Claude.ai chat exports and Claude Code CLI session transcripts: validates
them, recovers files Claude created during conversations, infers semantic structure,
and renders an interactive HTML dashboard.

---

## Critical naming convention

**`conversations`** = the data format and schema name (`conversations.json`,
`rsc/schema/conversations/`).

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

- Run `src/test/pre_commit.sh` before and after any change. Score must not drop below perfection. Expected score is tracked in [`src/test/pre_commit_expected_score`](src/test/pre_commit_expected_score) and checked automatically — update that file when new checks are added.
- Run `src/test/xref.sh` after structural changes to catch stale references. Currently 14 known non-issues (template placeholders, false positives); if this count changes, investigate before updating it here.
- `git clean -fdX; git clean -fdxn` after a full run — the output should be fully accounted for.

---

## Venv

`src/activate_venv.sh` is the single canonical activator. Path: `~/venvs/general`
(overridable via `$VENV`). Sets `trap deactivate EXIT` — callers never deactivate
manually. Dependencies: `requirements.txt`.

---

## Schema directories

Named after the data format they validate, not the pipeline:
`rsc/schema/conversations/` (currently v1–v6), `rsc/schema/session/` (currently v1),
`rsc/schema/apiConversation/` (currently v1).

`rsc/schema/apiConversation/v1.json` validates live claude.ai API responses (`ApiConversation`
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
src/main/browser-captures/safari_fetch_api_json.sh --captures ../browser-captures/data-<...>
```

Saves `{title}.json` alongside each `.md` and `.log`.

To validate the captured API JSON against `rsc/schema/apiConversation/v1.json`:

```bash
src/main/browser-captures/validate.sh --batch ../browser-captures/data-<...>
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
- Schemas: `rsc/schema/conversations/` (v1–v6), `rsc/schema/session/` (v1, singular!), `rsc/schema/apiConversation/` (v1)
- `rsc/schema/model_join.csv` — unified 4-way join: conversations ↔ session ↔ apiConversation ↔ MCP
- `src/test/gen_changelog_matrix.py` — generates CHANGELOG rows from gen/ logs for any pipeline
- Validation matrix driven by CHANGELOG.md files (not hardcoded constants) via `_parse_changelog_matrix()`
