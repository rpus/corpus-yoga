---
schema_file: rsc/schema/chat-exports/conversations/v6.json
principles_file: rsc/schema/chat-exports/conversations/principles.md
workflow_file: rsc/schema/chat-exports/conversations/workflow.md
version: "1.3"
---

# Schema Development Workflow for `rsc/schema/chat-exports/conversations/v{N}.json`

A living document describing the correct procedure for schema development sessions. This workflow should be followed by both human and agent participants. Deviations should be flagged, not silently accommodated.

This document has three sections: [Session Setup](#session-setup), [The Workflow Loop](#the-workflow-loop), and [Meta-Rules](#meta-rules). The workflow loop is the core — it applies whenever the schema is being modified or a new export is being incorporated.

---

## Base Principles

See [`rsc/schema/workflow.md`](../../workflow.md) for the four base principles, semantic versioning rules, and meta-rules shared across all pipelines.

---

---

## Session Setup

Before any schema work begins, the following artefacts must be available in the current session context. If any are missing, request them before proceeding.

| Artefact | Purpose | Source |
| --- | --- | --- |
| `v{N}.json` | The schema under development | Upload from `rsc/schema/chat-exports/conversations/` |
| `principles.md` | Design principles, diagnostics, repair snippets | Upload from `rsc/schema/chat-exports/conversations/` |
| `workflow.md` | This document | Upload from `rsc/schema/chat-exports/conversations/` |
| At least one `conversations.json` export | Ground-truth validation data | Upload from `ext/chat-exports/data-*/` |
| `conversations_redacted.json` (optional) | Safe-to-share compressed export for diagnostic work | Upload from `gen/` |

**Flag if:** the session begins with schema edits before any of the above are uploaded.

**Flag if:** the user uploads a schema but not the principles document — the two must be treated as a unit.

---

## Incorporating a new export (no schema change)

When a new export validates against the current schema without modification:

1. Run: `src/main/chat-exports/RUNME.sh --chat-export <path>`
2. Confirm all logs under `gen/chat-exports/<export>/validation/conversations/` contain `Valid!`.
3. Test the new export against **every** schema version, not just the latest — validate it against v1 through v{N} to fill every cell in the CHANGELOG matrix row.
4. Update the CHANGELOG matrix:

   ```bash
   src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline chat-exports --write
   ```

5. Run `src/test/pre_commit.sh` to confirm all new pairs are green.
6. Commit.

If the export fails any version, enter the Workflow Loop below.

---

## The Workflow Loop

The loop applies in two contexts: **diagnostic runs** (checking the current schema) and **incorporation runs** (adding a new export or making schema changes). Both follow the same steps; incorporation runs add steps 0 and 10.

### Step 0 · Incorporation only: Validate the new export

Run `Draft4Validator` against the new export. If it passes, the schema already covers the new data — skip to step 10 (update documentation). If it fails, note the first failing path and message, then continue to step 1.

```python
import json
from jsonschema import Draft4Validator
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
with open('conversations.json') as f:
    data = json.load(f)
errors = list(Draft4Validator(schema).iter_errors(data))
if errors:
    print(f'{len(errors)} error(s)')
    for e in errors[:5]:
        print(f'  Path: {list(e.absolute_path)}')
        print(f'  {e.message}')
else:
    print('Valid')
```

**Flag if:** schema changes are made before this step is run.

---

### Step 1 · Run all enforced diagnostics

Run every diagnostic marked `enforced` in `rsc/schema/chat-exports/conversations/principles.md`. Use the consolidated runner below. Record all failures.

```python
# Run from the consolidated diagnostics runner
# (paste the full runner from the principles doc, or run it as a script)
# Expected output: N/27 PASS
```

**Flag if:** schema edits are made before this step is complete.

**Flag if:** only some diagnostics are run rather than the full suite.

---

### Step 2 · Categorise failures by root cause

Group the diagnostic failures by underlying cause, not by diagnostic id. Multiple diagnostics may fire for a single root cause (e.g. a new definition missing `title`, `description`, and correct field order will fail three diagnostics but has one fix).

Present the categorised list to the user before proceeding. Example format:

```text
Root cause 1: HasNameDiscriminatorProperty missing title/description/field-order
  → fails: naming.title_matches_key, structure.field_order,
           documentation.every_definition_has_title_and_description

Root cause 2: BFS order has drifted
  → fails: structure.bfs_order

Root cause 3: RichContentItem null properties undocumented
  → fails: documentation.null_only_fields_documented
```

**Flag if:** the user requests fixes before this categorisation is presented.

---

### Step 3 · Triage: diagnostic refinements vs genuine schema issues

For each failure, determine whether it reflects:

- **(A) A diagnostic that is firing incorrectly** — the schema is fine, the check is too broad or lacks a necessary exception.
- **(B) A genuine schema issue** — the schema violates a principle and needs fixing.

This distinction is critical. **Always fix (A) before (B).** Fixing schema issues against a miscalibrated diagnostic may introduce or mask real problems.

Common causes of (A):

- A diagnostic has no exception for a known legitimate pattern (e.g. `ToolInput*` stubs are legitimately unreachable)
- A diagnostic checks anonymous inline schemas that don't warrant documentation
- A diagnostic uses a heuristic (e.g. "has `name` property") that catches schemas it shouldn't

**Flag if:** schema changes are made to satisfy a diagnostic that has not yet been confirmed as correctly calibrated.

---

### Step 4 · Fix diagnostic refinements

For each (A) failure, refine the diagnostic in `rsc/schema/chat-exports/conversations/principles.md`. Re-run the affected diagnostic after each refinement to confirm it now passes (or at least no longer fires spuriously).

Document the refinement rationale in the principles document alongside the diagnostic snippet. If a `KNOWN_EXCEPTIONS` set is introduced, list each exception with its justification.

**Flag if:** a diagnostic is silenced without a documented justification for the exception.

**Flag if:** a diagnostic is weakened to the point where it would no longer catch the failure it was designed to detect.

---

### Step 5 · Re-run all diagnostics

After all diagnostic refinements, re-run the full suite. Confirm that:

- Previously spurious failures are now passing.
- No new failures have been introduced by the refinements.
- Remaining failures are all genuine schema issues.

**Flag if:** this re-run is skipped and the user proceeds directly to schema fixes.

---

### Step 6 · Fix genuine schema issues

Fix each (B) failure using the repair snippets in `rsc/schema/chat-exports/conversations/principles.md`. Work through root causes in order of fundamentality — structural issues (missing definitions, wrong types) before documentation issues (missing descriptions, wrong descriptions).

For each fix:

1. Apply the repair.
2. Re-run the specific diagnostic that was failing.
3. Confirm it now passes before moving to the next fix.

Do not batch multiple independent root causes into a single edit without re-running between them.

**Flag if:** multiple unrelated schema changes are made in a single step without intermediate diagnostic runs.

**Flag if:** a fix is made that goes beyond what the diagnostic requires (scope creep).

---

### Step 7 · Run all diagnostics

Run the full suite again. Expected result: all `enforced` diagnostics pass.

If any still fail, return to step 3 for those failures.

**Flag if:** this step is skipped.

---

### Step 8 · Validate against all known exports

Run `Draft4Validator` against every known export. All must pass. A newly failing export means a schema change has introduced a regression.

```python
import json
from jsonschema import Draft4Validator
with open('rsc/schema/chat-exports/conversations/v{N}.json') as f:
    schema = json.load(f)
for export_file in [
    'conversations.json',           # latest export
    # add further export paths here
]:
    with open(export_file) as f:
        data = json.load(f)
    errors = list(Draft4Validator(schema).iter_errors(data))
    status = 'Valid' if not errors else f'{len(errors)} error(s)'
    print(f'{export_file}: {status}')
```

**Flag if:** this step is skipped.

**Flag if:** a regression is silently accepted rather than investigated.

---

### Step 9 · Reissue the schema

Present the updated schema file for download. Note the line count and byte count in the session (matching the format used in `gen/<export>/validation/conversations/v{N}.log`).

**Flag if:** the schema is modified after this point without restarting the loop from step 1.

---

### Step 10 · Update documentation

Update `rsc/schema/chat-exports/conversations/principles.md` if any of the following occurred:

- A diagnostic was refined (update the snippet and add exception rationale).
- A new principle was identified (add a new entry in the appropriate category).
- A new open question arose (add to the Open Questions section).
- A repair snippet was used and found to need improvement (update the snippet).
- An open question was resolved (move it to an appropriate principle, remove from Open Questions).

Update this workflow document (`rsc/schema/chat-exports/conversations/workflow.md`) if the loop itself was found to be incomplete or incorrect.

**Flag if:** principles or workflow documents are left out of sync with actual practice.

---

### Step 11 · Commit

The session's outputs should be committed to the repository:

- Updated schema `v{N}.json` → `rsc/schema/chat-exports/conversations/`
- Updated `principles.md` → `rsc/schema/chat-exports/conversations/`
- Updated `workflow.md` → `rsc/schema/chat-exports/conversations/`
- Updated validation logs in `gen/` (from running `src/main/chat-exports/validate.sh`)

Commit message should note what changed: new export incorporated, schema fixes applied, diagnostic refinements, or documentation updates.

---

## Creating a New Schema Version

Schema versions follow **semantic versioning** (see <https://semver.org>) from v6 onward. Versions v1–v6 are legacy integer versions; their naming is retained as-is.

```text
MAJOR.MINOR.PATCH   e.g. v6.1.0, v7.0.0
```

| Component | Meaning | Trigger |
| --- | --- | --- |
| **MAJOR** | Breaking | A **material restriction**: a change that causes at least one currently-passing export to fail |
| **MINOR** | Non-breaking extension | A **relaxation** or **non-material restriction**: more exports pass, none fail |
| **PATCH** | No validation effect | **Refactored** only: structural changes, description updates, repairs |

File naming mirrors this: `v6.1.0.json`, `v7.0.0.json`, etc. `pre_commit.py` detects the highest version automatically via glob.

### When to bump

| Change type | Bump | Action |
| --- | --- | --- |
| Relaxed (new optional field, new `oneOf` branch) | MINOR | Copy to new MINOR file |
| Restricted — material (causes a passing export to fail) | MAJOR | Copy to new MAJOR file |
| Restricted — non-material (no known export uses the value) | MINOR | Copy to new MINOR file; note as non-material in CHANGELOG |
| Refactored (no validation effect) | PATCH | Copy to new PATCH file, or edit in place if PATCH = 0 |

**Flag if:** a restriction is applied without first verifying whether it is material (run all passing exports through the new schema before deciding the bump level).

### Steps to create a new version

1. Determine the correct bump level (MAJOR/MINOR/PATCH) from the table above, then copy: `cp rsc/schema/chat-exports/conversations/v{current}.json rsc/schema/chat-exports/conversations/v{new}.json`

### No todo

1. Make the schema changes in `v{N+1}.json`. Every new definition must have `title` and `description` from the outset — the diagnostic suite will fail on these immediately and noisily if they are absent, obscuring other failures. No TODO placeholders.
2. Run the full workflow loop (steps 1–11) against `v{N+1}.json`.
3. Test every known export against the new version to establish which pass:

   ```bash
   source src/activate_venv.sh
   for d in /path/to/chat-exports/data-*/; do
     result=$(python src/main/validate.py "$d/conversations.json" rsc/schema/chat-exports/conversations/v{N+1}.json 2>&1)
     echo "$d: $(echo "$result" | grep -q Valid && echo ✓ || echo ✗)"
   done
   ```

   For any export not already present in the matrix, also test it against every prior version — do not infer its earlier results from the fact that it is new.

### Changelog narrative

1. Add a `## v{N+1}` section to `CHANGELOG.md` with **Relaxed**, **Restricted**, and/or **Refactored** subsections as appropriate. Only include categories that apply. Also update the matrix ✓/✗ column for all exports.

### Changelog entry

1. Update the CHANGELOG matrix:

   ```bash
   src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline chat-exports --write
   ```

   `pre_commit.py` reads this matrix directly — no constants to update.

### Finishing up

1. Review diagnostic exception sets in `src/test/diagnostics/`:
   - `KNOWN_UNREACHABLE` in `structure.all_definitions_reachable.py` — add any new intentional stubs; remove entries for definitions that have become reachable or been removed.
   - `KNOWN_CLOSED` in `documentation.open_set_enums_documented.py` — add any newly confirmed closed enum sets; remove entries that no longer appear in the schema.
   - Every entry must include a `# v{N}+` version annotation stating when it was added.
2. Review `rsc/schema/model_join.csv`:
   - The unified four-way table covers definitions with notable correspondences across conversations, session, apiConversation, and MCP — not every definition needs a row.
   - For any definition added that has a meaningful counterpart in another schema (or a noteworthy absence), add rows describing the relationship.
   - For any definition removed that has rows in the table, delete or update those rows.
   - `src/test/pre_commit.sh` validates all JSON Pointer fragments in the file — a failing pointer means a row references a definition that no longer exists in the schema.
3. Run `src/main/model/gen_model.sh` and review the output in `gen/model/` — update `rsc/schema/model.json` if any cross-schema identifiers changed.
4. Generate validation logs for the new pairs: `src/main/chat-exports/RUNME.sh --chat-exports <path/to/chat-exports>`
   Note: step 5 depends on these logs existing — `pre_commit.sh` will fail on missing logs, not on schema errors, which is misleading. Always run `validate.sh` before `pre_commit.sh`.
5. Run `src/test/pre_commit.sh` and confirm all checks pass.

**Flag if:** `CHANGELOG.md`, `model_join.csv`, and the diagnostic exception sets are not all reviewed in the same session as the new version file.

---

## Meta-Rules

See [`rsc/schema/workflow.md`](../../workflow.md) for the full meta-rules shared across all pipelines.

---

## Worked Example

The following is a condensed example trace of a correctly executed workflow loop, as a reference for future sessions.

```text
Upload: rsc/schema/chat-exports/conversations/v{N}.json (1,965 lines), conversations.json (115,509 lines)

Step 1: Run all enforced diagnostics → 11/27 PASS

Step 2: Categorise failures:
  Root cause A1 (diagnostic): all_definitions_reachable fires on known stubs
  Root cause A3 (diagnostic): null_only_fields_documented fires on anonymous oneOf branches
  Root cause A4 (diagnostic): open_set_enums_documented fires on known closed sets
  Root cause A5 (diagnostic): discriminator_fields_annotated fires on non-discriminator enums
  Root cause A6 (diagnostic): discriminated_union_pattern fires on nullability oneOfs
  Root cause A7 (diagnostic): no_additional_properties_on_subtypes definition too loose
  Root cause B1 (schema): Has*DiscriminatorProperty missing title/description/field-order
  Root cause B2 (schema): BFS order has drifted
  Root cause B3 (schema): RichContentItem null properties undocumented
  Root cause B4 (schema): ToolInputRecommendClaudeApps.app_ids.items missing open-set caveat

Step 3: Triage → A1–A7 are diagnostic issues, B1–B4 are schema issues

Steps 4–5: Refine diagnostics A1–A7, re-run → 16/27 PASS (only B1–B4 remaining)

Step 6: Fix B1 (title/description/field-order) → reissue schema
         Fix B2 (BFS reorder) → reissue schema
         Fix B3 (null property descriptions) → verify empirically first → reissue schema
         Fix B4 (open-set caveat) → reissue schema

Step 7: Re-run all diagnostics → 22/27 PASS

Step 8: Validate against all exports → Valid

Step 9: Reissue schema (1,974 lines, 61,225 bytes)

Step 10: Update principles.md with refined diagnostics and repair snippets
         Bump version 1.0 → 1.1

Step 11: Commit
```

---

*This document was written after the first complete enactment of the workflow loop. It should be updated whenever the loop is found to be incomplete or incorrect in practice.*
