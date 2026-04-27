---
schema_file: rsc/schema/claude-code-sessions/v1.json
workflow_file: rsc/schema/claude-code-sessions/workflow.md
version: "1.0"
---

# Schema Development Workflow for `claude-code-sessions`

A living document describing how to maintain and extend the CLI sessions schema.
Follows the same philosophy as `rsc/schema/conversations/workflow.md` but adapted
to the different lifecycle of CLI session data.

---

## Base Principles

The general schema design principles in `rsc/schema/conversations/principles.md` apply to this
schema. `principles.md` in this directory documents the adaptations and known
deviations. The same four workflow principles apply here:

1. **Try to follow these instructions.** Follow the workflow even when it feels like overhead.
2. **Flag if anything seems wrong.** An anomaly is information; don't paper over it.
3. **Flag if the user does something wrong.** Flagging is a checkpoint, not refusal.
4. **Suggest improvements.** The schema, `cli_join.csv`, and this document are all living.

---

## Overview: Two Lifecycles

The CLI sessions schema has two distinct update triggers with different cadences:

**Session data updates continuously.** `../code-sessions/` is a directory of symlinks into
`~/.claude/projects/`. Claude Code writes to `.jsonl` files in real time during every
session. The symlinks expose the current on-disk state with no caching layer — a file
read through the symlink is always current. Running `RUNME-code-sessions.sh` produces
a snapshot in `gen/code-sessions/` from whatever is in the `.jsonl` files at that moment.

**The schema updates rarely.** `v1.json` only changes when a new field, record type,
or value is observed in a session that the current schema cannot validate. The schema
should be updated conservatively — every constraint reflects empirical observation, and
relaxations must be justified by actual data.

---

## Adding a New Project

To add sessions for a repository not yet in `../code-sessions/`:

```bash
# Run from the target repo's root:
ln -sfn "$HOME/.claude/projects/$(pwd | sed 's|/|-|g')" \
        ../code-sessions/my-project-name
```

Then run `RUNME-code-sessions.sh` to validate the new sessions. If any fail, follow
the validation loop below.

---

## The Validation Loop

Run this whenever new sessions appear or the schema changes.

### Step 1 · Run RUNME-code-sessions.sh

```bash
./RUNME-code-sessions.sh
```

For each session, this converts the `.jsonl` to a JSON array and validates it against
`v1.json`. Output: `Valid!` or a first-failing record with path information.

**Flag if:** schema changes are made before this step is run against the current sessions.

---

### Step 2 · Run diagnostics

```bash
python src/test/pre_commit.py
```

This runs all 25 schema diagnostics against `v1.json` (the same suite as the
conversations schema, minus `composition.base_schemas_closed` — see `principles.md`).
All should pass; failures indicate structural issues in the schema independent of any
specific session data.

If sessions fail validation (step 1), use the debug script to identify the record-level cause:

```bash
python src/test/debug_code_session_record.py \
  gen/code-sessions/{project}/{session}/session.json
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

Fix one root cause at a time. Re-run `RUNME-code-sessions.sh` after each fix to confirm
it resolved the failure and introduced no regressions.

---

### Step 4 · Update CHANGELOG.md

After all sessions validate, record what changed:

- Add any new fields, record types, or block types to the relevant section
- Move open questions to resolved if the data has clarified them
- Note new open questions if new ambiguities were discovered

---

### Step 5 · Update cli_join.csv

Review `cli_join.csv` for any new fields added in step 3:

- If a new field has a counterpart in `rsc/schema/conversations/v6.json` or `mcp.json`, add a row
- If a new field is CLI-only, add a row with `cli_only` relationship and empty `conv_path`/`mcp_path`
- If a field was removed or renamed, delete or update its rows
- Not every field needs a row — only those with notable correspondences or notable absences

Run `python src/test/pre_commit.py` to verify all pointers in the updated table.

**Flag if:** `v1.json` changes but `cli_join.csv` is not reviewed.

---

### Step 5b · Record the validation fingerprint in CHANGELOG.md

Each validation log records the JSONL byte size at the time of validation:

```text
2026-04-26T17:06:54+01:00
.../60c07575....jsonl: 7248 lines, 18899859 bytes
...
Valid!
```

After a successful run, update the CHANGELOG matrix with the current line and byte counts
from the log. Since JSONL files are append-only, the byte count is a precise fingerprint:
it records exactly how much of the session was validated. A later run with a larger byte
count means more of the session was covered.

**Flag if:** the CHANGELOG matrix is not updated after a validation run.

---

### Step 6 · Run pre_commit.py

```bash
source ~/venvs/general/bin/activate && python src/test/pre_commit.py
```

Confirms `cli_join.csv` pointers are valid and the conversations schema diagnostics
still pass. Expect the existing PASS count plus the new `cli_join.csv` check.

---

## cli_join.csv Maintenance

`cli_join.csv` is a field-level correspondence table — CLI sessions ↔ conversations
export ↔ MCP protocol. It does not update automatically. Review it whenever:

| Trigger | Action |
| --- | --- |
| `v1.json` gains a new field | Add rows for any counterparts; `cli_only` if none |
| A new schema version is cut | Update `cli_path` pointers to the new version file |
| `conversations/v{N}.json` updates | Check if new conv fields have CLI equivalents |
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
| **PATCH** | No validation effect | Refactor, description update, `cli_join.csv` update only |

### Steps

1. Determine the correct bump level from the table above.
2. Copy the current version: `cp v1.json v{N+1}.json`
3. Make the schema changes in `v{N+1}.json`.
4. Run the validation loop (steps 1–6 above) against `v{N+1}.json`.
5. Test every known session against the new version.
6. Update `CHANGELOG.md`: add the new version row to the matrix, fill ✓/✗ for all
   sessions, add a section describing what changed.
7. Update `cli_join.csv` `cli_path` pointers to reference `v{N+1}.json`.
8. Run `pre_commit.py` to confirm all checks pass.

---

## Real-time vs Snapshot

| | `../code-sessions/{project}/*.jsonl` | `gen/code-sessions/{project}/{session}/` |
| --- | --- | --- |
| **Updated** | Continuously, by Claude Code | Only when `RUNME-code-sessions.sh` is run |
| **Contents** | Live session data | Snapshot: converted JSON + validation log |
| **Current session** | Being written right now | Reflects state at last run |

Because the active session's `.jsonl` grows throughout a Claude Code session, re-running
`RUNME-code-sessions.sh` mid-session will validate a longer transcript than the previous
run. This is expected and useful — it catches new record types or field values that appear
only later in a session.

---

## Survey Script

When encountering sessions from a new project or Claude Code version, run the survey
script first to understand the data before attempting validation:

```bash
python src/test/survey_code_session.py ../code-sessions/{project}/*.jsonl
```

This reports all record types, field keys, discriminator values, content block types,
and tool names observed — the empirical grounding needed before writing or extending
the schema.

---

*This document was written after the initial schema development session that produced
`v1.json`. Update it whenever the loop is found to be incomplete or incorrect in practice.*
