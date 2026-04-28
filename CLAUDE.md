# CLAUDE.md

This file is the authoritative source for the project memory stored at
`~/.claude/projects/-Users-*-claude-export-yoga/memory/MEMORY.md`. If the memory diverges
from this file, flag it and suggest updating the memory to match — not the other way around.

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

---

## Pipelines

```bash
src/main/chat-exports/RUNME.sh  --chat-exports  ../chat-exports
src/main/code-projects/RUNME.sh --code-projects ../code-projects
```

---

## Key invariants

- Run `src/test/pre_commit.sh` before and after any change. Score must not drop (currently 111/111).
- Run `src/test/xref.sh` after structural changes to catch stale references.
- `git clean -fdX; git clean -fdxn` after a full run — the output should be fully accounted for.

---

## Venv

`src/activate_venv.sh` is the single canonical activator. Path: `~/venvs/general`
(overridable via `$VENV`). Sets `trap deactivate EXIT` — callers never deactivate
manually. Dependencies: `requirements.txt`.

---

## Schema directories

Named after the data format they validate, not the pipeline:
`rsc/schema/conversations/` (currently v1–v6), `rsc/schema/sessions/` (currently v1).

---

## Design principle: look the same if and only if the same

Things that are functionally equivalent should look structurally identical; things that differ should
look different. Unexplained asymmetry is always a signal — either the asymmetry is
meaningful (document it) or it is accidental (fix it). This applies at every level:
schema definitions, function names, section headers, variable names, file layout,
flag names, and documentation structure.
Structural symmetry, meanwhile, allows for easy factoring of commonality.
