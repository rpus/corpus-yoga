---
schema_file: rsc/schema/code-projects/session/v1.json
principles_file: rsc/schema/code-projects/session/principles.md
workflow_file: rsc/schema/code-projects/session/workflow.md
version: "1.0"
---

# Schema Development Workflow for `rsc/schema/code-projects/session/v{N}.json`

A living document describing how to maintain and extend the CLI session schema.
Follows the same philosophy as `rsc/schema/chat-exports/conversations/workflow.md` but adapted
to the different lifecycle of CLI session data.

---

## Base Principles

The general schema design principles in `rsc/schema/chat-exports/conversations/principles.md` apply to this
schema. `principles.md` in this directory documents the adaptations and known
deviations. The same four workflow principles apply here:

1. **Try to follow these instructions.** Follow the workflow even when it feels like overhead.
2. **Flag if anything seems wrong.** An anomaly is information; don't paper over it.
3. **Flag if the user does something wrong.** Flagging is a checkpoint, not refusal.
4. **Suggest improvements.** The schema, `model_join.csv`, and this document are all living.

---

## Overview: Two Lifecycles

The CLI session schema has two distinct update triggers with different cadences:

**Session data updates continuously.** `../code-projects/` is a symlink directly to
`~/.claude/projects/`. Claude Code writes to `.jsonl` files in real time during every
session. Reading through the symlink is always current — no caching layer. Running
`src/main/code-projects/RUNME.sh` produces a snapshot in `gen/code-projects/` from whatever is
in the `.jsonl` files at that moment.

**The schema updates rarely.** `v1.json` only changes when a new field, record type,
or value is observed in a session that the current schema cannot validate. The schema
should be updated conservatively — every constraint reflects empirical observation, and
relaxations must be justified by actual data.

---

## Adding a New Project

`../code-projects/` is a symlink directly to `~/.claude/projects/`, so any project
Claude Code has ever run in is already present — no manual setup required.

To run for a specific project, pass its path inside `../code-projects/`:

```bash
# From within the target repo:
./src/main/code-projects/RUNME.sh --code-project "../code-projects/$(pwd | tr '/' '-')"
```

Then follow the validation loop below if any sessions fail.

---

## The Validation Loop

Run this whenever new sessions appear or the schema changes.

### Step 1 · Run src/main/code-projects/RUNME.sh

```bash
./src/main/code-projects/RUNME.sh
```

For each session, this converts the `.jsonl` to a JSON array and validates it against
`v1.json`. Output: `Valid!` or a first-failing record with path information.

**Flag if:** schema changes are made before this step is run against the current sessions.

---

### Step 2 · Run diagnostics

```bash
src/test/pre_commit.sh
```

This runs all schema diagnostics against the latest sessions schema (the same suite as
the conversations schema, minus `composition.base_schemas_closed` — see `principles.md`).
All should pass; failures indicate structural issues in the schema independent of any
specific session data.

If sessions fail validation (step 1), use the debug script to identify the record-level cause:

```bash
python src/test/code-projects/debug_code_session_record.py \
  ../code-projects/{project-slug}/{session}.jsonl
```

This tests each branch of `Record.oneOf` against the failing record and drills into
the matching subtype to find the leaf-level error path. Use `--all` to see all failures
at once, `--index N` for a specific record.

**Read the error carefully before touching the schema.** Common categories:

- **New field on a known record type** — `additionalProperties: false` rejected it.
  Add the field to the schema with the correct type. Do not simply remove the constraint.
- **New type for an existing field** — a field typed as `string` appears as `object`
  or vice versa. Widen to `"type": ["string", "object"]` (array form, not `oneOf`) if
  genuinely polymorphic; or correct a wrong initial assumption.
- **New record type** — a `type` value not in `Record.oneOf`. Add a new definition
  following the wrapper/base/subtype pattern.
- **New content block type** — a `type` value not in `ContentBlock.oneOf`. Add a new
  block definition.

**Flag if:** a type constraint is removed entirely rather than correctly typed. The schema
must be as restrictive as the data allows — loosening to get a green light defeats the
purpose.

---

### Step 3 · Fix the schema

Fix one root cause at a time. Re-run `src/main/code-projects/RUNME.sh` after each fix to confirm
it resolved the failure and introduced no regressions.

---

### Step 4 · Update CHANGELOG.md

After all sessions validate, record what changed:

- Add any new fields, record types, or block types to the relevant section
- Move open questions to resolved if the data has clarified them
- Note new open questions if new ambiguities were discovered

---

### Step 5 · Update model_join.csv

Review `rsc/schema/model_join.csv` for any new fields added in step 3.
`model_join.csv` is the unified four-way table (session ↔ conversations ↔ apiConversation ↔ MCP):

- If a new field has a counterpart in another schema, add a row with the matching `session_path`, `conv_path`, `api_path`, and/or `mcp_path`
- If a new field is session-only, add a row with `session_only` relationship and empty other columns
- If a field was removed or renamed, delete or update its rows
- Not every field needs a row — only those with notable correspondences or notable absences

Run `src/test/pre_commit.sh` to verify all pointers in the updated table.

**Flag if:** `v1.json` changes but `model_join.csv` is not reviewed.

---

### Step 5b · Record the validation fingerprint in CHANGELOG.md and pre_commit.py

Each validation log records the JSONL byte size at the time of validation:

```text
2026-04-26T17:06:54+01:00
.../60c07575....jsonl: 7248 lines, 18899859 bytes
.../rsc/schema/code-projects/session/v1.json: 27568 bytes
Valid!
```

After a successful run:

1. Update the CHANGELOG.md matrix with the current line and byte counts from the log.
   Since JSONL files are append-only, the byte count is a precise fingerprint: it records
   exactly how much of the session was validated. A later run with a larger byte count
   means more of the session was covered. For a **new** session (first time in the matrix),
   add a new row; for an existing session, update the counts.

2. Add each new row to `rsc/schema/code-projects/session/CHANGELOG.md` using bare project name and
   8-character UUID prefix (e.g. `claude-export-yoga / 46fcb702`).
   `pre_commit.py` reads the matrix directly — no separate constant to update.

**Flag if:** the CHANGELOG matrix is not updated after a validation run that adds new passing sessions.

`pre_commit.py` enforces this with a closed-world complement: any session log found in
`gen/code-projects/` that is absent from the CHANGELOG matrix raises a failure —
whether the session passes (unregistered) or fails (undetected). This catches sessions
from projects added automatically to `../code-projects/` that were never explicitly
recorded.

---

### Step 6 · Run pre_commit.sh

```bash
src/test/pre_commit.sh
```

Confirms all checks pass, including `model_join.csv` pointer validity and the session schema diagnostics.

---

## model_join.csv Maintenance

`rsc/schema/model_join.csv` is the unified four-way field-level correspondence table
(session ↔ conversations ↔ apiConversation ↔ MCP). It does not update automatically.
Review it whenever:

| Trigger | Action |
| --- | --- |
| `v1.json` gains a new field | Add rows for any counterparts; `session_only` if none |
| A new schema version is cut | Update `session_path` pointers to the new version file |
| Any other schema updates | Check if new fields have session equivalents |
| An open question in CHANGELOG is resolved | Update the corresponding `note` cell |

The `pre_commit.py` pointer check ensures existing rows stay valid as schemas evolve,
but does not detect missing rows. Missing rows are a documentation gap, not a build
failure.

---

## Creating a New Schema Version

Schema versions use **semantic versioning** from v1 onward:

| Component | Meaning | Trigger |
| --- | --- | --- |
| **MAJOR** | Breaking | A material restriction: a currently-passing session now fails |
| **MINOR** | Non-breaking extension | A relaxation or non-material restriction: more sessions pass |
| **PATCH** | No validation effect | Refactor, description update, `model_join.csv` update only |

### Steps

1. Determine the correct bump level from the table above.
2. Copy the current version: `cp v1.json v{N+1}.json`
3. Make the schema changes in `v{N+1}.json`.
4. Run the validation loop (steps 1–6 above) against `v{N+1}.json`.
5. Test every known session against the new version.
6. Update `CHANGELOG.md`: add the new version row to the matrix, fill ✓/✗ for all
   sessions, add a section describing what changed.
7. Update `model_join.csv` `cli_path` pointers to reference `v{N+1}.json`.
8. Run `src/test/pre_commit.sh` to confirm all checks pass.

---

## Real-time vs Snapshot

| | `../code-projects/{project-slug}/*.jsonl` | `gen/code-projects/{project-slug}/{session}/` |
| --- | --- | --- |
| **Updated** | Continuously, by Claude Code | Only when `src/main/code-projects/RUNME.sh` is run |
| **Contents** | Live session data | Snapshot: converted JSON + validation log |
| **Current session** | Being written right now | Reflects state at last run |

Because the active session's `.jsonl` grows throughout a Claude Code session, re-running
`src/main/code-projects/RUNME.sh` mid-session will validate a longer transcript than the previous
run. This is expected and useful — it catches new record types or field values that appear
only later in a session.

---

## Survey Script

When encountering sessions from a new project or Claude Code version, run the survey
script first to understand the data before attempting validation:

```bash
python src/test/code-projects/survey_code_session.py ../code-projects/{project-slug}/*.jsonl
```

This reports all record types, field keys, discriminator values, content block types,
and tool names observed — the empirical grounding needed before writing or extending
the schema.

---

*This document was written after the initial schema development session that produced
`v1.json`. Update it whenever the loop is found to be incomplete or incorrect in practice.*
