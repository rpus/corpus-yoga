# Pipeline Model

This document describes all pipelines and schemas as a unified reference. It has two
purposes: (1) a comparative overview of the current state, and (2) a guide for adding
a new pipeline.

`src/test/pre_commit.py` derives its checks from a `PIPELINES` data structure — a
`Pipeline` dataclass and dict driving two generic check functions. Adding a new pipeline
requires only a new `PIPELINES` entry; no new functions.

---

## Pipelines

| Property | `chat-exports` | `code-projects` | `browser-captures` |
| --- | --- | --- | --- |
| **Input dir** | `../chat-exports/` | `../code-projects/` | `../browser-captures/` |
| **Gen dir** | `gen/chat-exports/` | `gen/code-projects/` | `gen/browser-captures/` |
| **Validate script** | `src/main/chat-exports/validate.sh` | `src/main/code-projects/RUNME.sh` | `src/main/browser-captures/RUNME.sh` |
| **Subject depth** | 1 — `data_dir` | 2 — `project / session` | 2 — `batch / conversation` |
| **Subject match** | exact | prefix (8-char UUID) | prefix (8-char UUID) |
| **Input glob** | `data-*/` | `-Users-*/*.jsonl` | `data-*/*/` |
| **Log path** | `{data_dir}/validation/{schema}/{version}.log` | `{project}/{session}/validation/{schema}/{version}.log` | `{batch}/{conversation}/validation/{schema}/{version}.log` |
| **CHANGELOG** | `rsc/schema/chat-exports/conversations/CHANGELOG.md` | `rsc/schema/code-projects/session/CHANGELOG.md` | `rsc/schema/browser-captures/apiConversation/CHANGELOG.md` |
| **Schema(s)** | conversations, memories, projects, users | session | apiConversation |
| **Diag skips (extra)** | — | `composition.base_schemas_closed` | — |

---

## Schemas

| Schema | Pipeline | Versions | CHANGELOG | Diagnostic skips |
| --- | --- | --- | --- | --- |
| `conversations` | chat-exports | v1–v6 | ✓ | `naming.root_schema_title_matches_filename` |
| `memories` | chat-exports | v1 | — | `naming.root_schema_title_matches_filename` |
| `projects` | chat-exports | v1 | — | `naming.root_schema_title_matches_filename` |
| `users` | chat-exports | v1 | — | `naming.root_schema_title_matches_filename` |
| `session` | code-projects | v1 | ✓ | `naming.root_schema_title_matches_filename`, `composition.base_schemas_closed` |
| `apiConversation` | browser-captures | v1 | ✓ | `naming.root_schema_title_matches_filename` |

Non-versioned root schemas ([`documenter.json`](../rsc/schema/documenter.json), [`model.json`](../rsc/schema/model.json))
are checked by `check_root_schema_diagnostics` — they belong to no pipeline.

---

## Validation output structure

Each pipeline produces validation logs under `gen/`. Log paths follow the pattern:

```text
gen/{pipeline}/{subject...}/validation/{schema}/{version}.log
```

Where `{subject...}` has the depth shown in the pipeline table above. Examples:

```text
gen/chat-exports/data-2026-04-07-07-52-05-batch-0000/validation/conversations/v6.log
gen/code-projects/-Users-khalidkhan-dev-Anthropic-claude-export-yoga/46fcb702-…/validation/session/v1.log
gen/browser-captures/data-0fc4c1e0-…-ed936fdf-batch-0000/0e537a54-…/validation/apiConversation/v1.log
```

---

## Adding a new pipeline

1. **Add string constants** to the `# ── Repo layout ──` block in `pre_commit.py`:
   - Pipeline name: e.g. `NEW_PIPELINE = '{new-pipeline}'`
   - Schema name(s): e.g. `NEW_SCHEMA = 'newSchema'`

2. **Create the schema directory**: `rsc/schema/{new-pipeline}/{newSchema}/`
   - Add `v1.json` with `$schema`, `title`, `description`, `definitions`
   - Add `principles.md`, `workflow.md`, `README.md`
   - Follow the structure of `rsc/schema/code-projects/session/` as a template
   - (`CHANGELOG.md` is created automatically by step 7)

3. **Add to `VERSIONED_SCHEMA_DIAGNOSTICS_SKIP`** in `pre_commit.py`:

   ```python
   NEW_SCHEMA: _SKIP_BASE,
   ```

4. **Create the validate script**: `src/main/{new-pipeline}/validate.sh`
   - Reads input from `../{new-pipeline}/`
   - Writes logs to `gen/{new-pipeline}/{subject}/validation/{newSchema}/{version}.log`
   - Follow `src/main/browser-captures/validate.sh` or `src/main/code-projects/validate.sh` as template

5. **Add a `PIPELINES` entry** in `pre_commit.py`:

   ```python
   '{new-pipeline}': Pipeline(
       schemas       = [NEW_SCHEMA],
       changelog     = RSC_SCHEMA / NEW_PIPELINE / NEW_SCHEMA / 'CHANGELOG.md',
       gen           = GEN / NEW_PIPELINE,
       input         = REPO_PARENT / NEW_PIPELINE,
       input_glob    = '...',        # pattern matching input subjects
       subject_depth = 1,            # or 2 — see Pipelines table above
       validate_cmd  = f'src/main/{NEW_PIPELINE}/RUNME.sh --{new-pipeline}',
   ),
   ```

   No separate validity or validation-output functions needed — the generic
   `check_pipeline_validity` and `check_pipeline_validation_outputs` pick it up
   automatically from `PIPELINES`.

6. **Run the validate script** to populate `gen/`:

   ```bash
   src/main/{new-pipeline}/RUNME.sh --{new-pipeline} ../{new-pipeline}
   ```

7. **Populate the CHANGELOG** in `rsc/schema/{newSchema}/CHANGELOG.md`:

   ```bash
   src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline {new-pipeline} --write
   ```

8. **Run `src/test/pre_commit.sh`**: confirm all checks pass. Commit the updated
   `src/test/pre_commit.log` so the diff shows what changed.

9. **Run `src/test/xref.sh`**: confirm no bad-pointer entries. Commit the updated
   `src/test/xref.csv` so the diff shows what references changed.

---

## Resolved: PIPELINES-as-data ✓

All three asymmetries above have been implemented. `pre_commit.py` now contains a
`Pipeline` dataclass and a `PIPELINES` dict driving two generic functions
(`check_pipeline_validity`, `check_pipeline_validation_outputs`) that replace the
six former per-pipeline functions. Adding a new pipeline now requires only a new
`PIPELINES` entry and a schema directory — no new functions.
