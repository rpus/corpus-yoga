# Schema Development Workflow — All Pipelines

Shared workflow foundations for all schemas in `rsc/schema/`. Each per-pipeline
`workflow.md` defers to this document for base principles, versioning, and meta-rules,
then describes its own pipeline-specific loop.

---

## Base Principles

Everything in any schema workflow is a specialisation of these four principles. When in
doubt, return to them.

1. **Try to follow the workflow.** It exists for good reasons. Follow it even when it
   feels like overhead — especially when it feels like overhead. Shortcuts taken under
   time pressure are where mistakes happen.

2. **Flag if anything seems wrong.** If a step produces an unexpected result, if a
   principle seems to conflict with the schema, if a diagnostic fires in a surprising
   way — flag it before proceeding. Do not silently paper over anomalies. An anomaly
   is information.

3. **Flag if the user does something wrong.** If the user skips a step, makes changes
   out of order, or requests something that violates a principle, say so explicitly
   before complying. Flagging is not refusal — it is a checkpoint. The user may have a
   good reason to deviate; the flag ensures the deviation is conscious and recorded.

4. **Suggest improvements.** When a diagnostic could be more precise, when a repair
   snippet could be cleaner, when a new principle seems to be emerging from practice —
   say so. The schema, principles, and workflow documents are all living; they improve
   through use.

---

## Semantic Versioning

All schema versions follow semantic versioning:

| Component | Meaning | Trigger |
| --- | --- | --- |
| **MAJOR** | Breaking | A material restriction: a currently-passing input now fails |
| **MINOR** | Non-breaking extension | A relaxation or non-material restriction: more inputs pass |
| **PATCH** | No validation effect | Refactor, description update, `model_join.csv` update only |

When creating a new version:

1. Determine the correct bump level from the table above.
2. Copy the current version: `cp v{N}.json v{N+1}.json`
3. Make changes in `v{N+1}.json`. Fill in all `description` fields — no TODO placeholders.
4. Run the pipeline's validation loop (steps in the per-pipeline `workflow.md`).
5. Add a `## v{N+1}` section to `CHANGELOG.md` with **Relaxed**, **Restricted**, and/or
   **Refactored** subsections as appropriate.
6. Update the CHANGELOG matrix:

   ```bash
   src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline <pipeline> --write
   ```

7. Review `rsc/schema/model_join.csv` for new or changed fields.
8. Run `src/test/pre_commit.sh` — commit the updated `pre_commit.log`.
9. Run `src/test/xref.sh` — commit the updated `xref.csv`.

**Flag if:** `CHANGELOG.md` and `model_join.csv` are not reviewed in the same session as
the new version file.

---

## Meta-Rules

These rules apply throughout any schema development session.

### Diagnostics before fixes

Never modify the schema to satisfy a diagnostic before confirming the diagnostic is
correctly calibrated. A passing diagnostic suite against a miscalibrated set of checks
is worse than a failing suite against correct checks — it creates false confidence.

### One root cause at a time

Fix one root cause per step, re-running diagnostics between each. This makes regressions
immediately visible and keeps the commit history meaningful.

### Validate after every schema change

Every schema change, however small, must be followed by a validation run against all
known inputs before the schema is considered correct. Diagnostics and validation are
complementary: diagnostics check structural principles; validation checks empirical
correctness.

### Categorise before fixing

Always present the categorised root causes before beginning fixes. This gives the user
the opportunity to reprioritise or identify additional context.

### Flag, don't silently accommodate

If the user skips a step or requests something that violates a meta-rule, flag it
explicitly before complying. Flagging is a checkpoint, not refusal.

### The principles document is the authority

If a diagnostic conflicts with an intuition about what the schema should look like, the
diagnostic wins until `principles.md` is explicitly updated. Ad hoc exceptions not
reflected in `principles.md` are technical debt.
