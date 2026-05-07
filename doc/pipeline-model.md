# Pipeline Model

This document describes all pipelines and schemas as a unified reference. It has two
purposes: (1) a comparative overview of the current state, and (2) a guide for adding
a new pipeline.

The eventual goal is for `src/test/pre_commit.py` to derive its checks from a `PIPELINES`
data structure rather than from parallel per-pipeline functions. This document describes
what that structure would need to capture.

---

## Pipelines

| Property | `chat-exports` | `code-projects` | `browser-captures` |
| --- | --- | --- | --- |
| **Input dir** | `../chat-exports/` | `../code-projects/` | `../browser-captures/` |
| **Gen dir** | `gen/chat-exports/` | `gen/code-projects/` | `gen/browser-captures/` |
| **Validate script** | `src/main/chat-exports/validate.sh` | `src/main/code-projects/RUNME.sh` | `src/main/browser-captures/validate.sh` |
| **Subject depth** | 1 — `data_dir` | 2 — `project / session` | 2 — `batch / conversation` |
| **Subject match** | exact | prefix (8-char UUID) | prefix (8-char UUID) |
| **Input glob** | `data-*/` | `-Users-*/*.jsonl` | `data-*/*/` |
| **Log path** | `{data_dir}/validation/{schema}/{version}.log` | `{project}/{session}/validation/{schema}/{version}.log` | `{batch}/{conversation}/validation/{schema}/{version}.log` |
| **CHANGELOG** | `rsc/schema/conversations/CHANGELOG.md` | `rsc/schema/session/CHANGELOG.md` | `rsc/schema/apiConversation/CHANGELOG.md` |
| **Schema(s)** | conversations, memories, projects, users | session | apiConversation |

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

Non-versioned root schemas ([`data-table.json`](../rsc/schema/data-table.json),
[`documenter.json`](../rsc/schema/documenter.json), [`model.json`](../rsc/schema/model.json))
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

2. **Create the schema directory**: `rsc/schema/{newSchema}/`
   - Add `v1.json` with `$schema`, `title`, `description`, `definitions`
   - Add `principles.md`, `workflow.md`, `CHANGELOG.md`, `README.md`
   - Follow the structure of `rsc/schema/session/` as a template

3. **Add to `VERSIONED_SCHEMA_DIAGNOSTICS_SKIP`** in `pre_commit.py`:

   ```python
   NEW_SCHEMA: _SKIP_BASE,
   ```

4. **Create the validate script**: `src/main/{new-pipeline}/validate.sh`
   - Reads input from `../{new-pipeline}/`
   - Writes logs to `gen/{new-pipeline}/{subject}/validation/{newSchema}/{version}.log`
   - Follow `src/main/browser-captures/validate.sh` or `src/main/code-projects/validate.sh` as template

5. **Add a validity check function** in `pre_commit.py`:

   ```python
   def check_new_pipeline_validity(run):
       versions = _sorted_versions(RSC_SCHEMA / NEW_SCHEMA)
       ...
   ```

6. **Run the validate script** to populate `gen/`:

   ```bash
   src/main/{new-pipeline}/validate.sh --batches ../{new-pipeline}
   ```

7. **Populate the CHANGELOG** in `rsc/schema/{newSchema}/CHANGELOG.md`:

   ```bash
   src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline {new-pipeline} --write
   ```

8. **Add a validation output check function** in `pre_commit.py`:
   - Parse the CHANGELOG with `_parse_changelog_matrix`
   - Check registered entries have logs and pass/fail as expected
   - Add closed-world complement (gen/ scan for unregistered entries)
   - Add input scan (`../{new-pipeline}/` scan for unregistered subjects)
   - Follow `check_browser_captures_validation_outputs` as the current template

9. **Wire into `main()`**: add `run_section(check_new_pipeline_validity)` and
   `run_section(check_new_pipeline_validation_outputs)` in definition order.

10. **Run `src/test/pre_commit.sh`**: confirm all checks pass. If the score changed,
    update it in `CLAUDE.md` (Key invariants line).

11. **Run `src/test/xref.sh`**: confirm no new bad-pointer or missing-file entries
    beyond the known non-issues. If the count changed, update it in `CLAUDE.md` (Key invariants line).

---

## Current asymmetries in pre_commit.py

Three sets of parallel per-pipeline functions exist where a single generic function
driven by data should:

1. **`check_{pipeline}_validity`** — `check_browser_captures_validity`,
   `check_chat_exports_validity`, `check_code_projects_validity` each explicitly list
   their schemas. This should be derived from `PIPELINES[pipeline].schemas`.

2. **`check_{pipeline}_validation_outputs`** — three nearly-identical functions
   (parse CHANGELOG, check registered entries, closed-world complement, input scan)
   differing only in path structure and subject depth. One generic function parameterised
   by the pipeline descriptor would replace all three.

3. **`VERSIONED_SCHEMA_DIAGNOSTICS_SKIP`** is already schemas-as-data. It has no
   companion `PIPELINES` structure, so the pipeline ↔ schema relationship is implicit
   (scattered across the validity functions) rather than explicit.

---

## What PIPELINES-as-data would look like

Steps 5, 8, and 9 above are currently written as per-pipeline functions. The eventual
goal is to replace them with a single `PIPELINES` dict and generic functions:

```python
PIPELINES = {
    CHAT_EXPORTS: Pipeline(
        schemas       = [CONVERSATIONS, MEMORIES, PROJECTS, USERS],
        changelog     = RSC_SCHEMA / CONVERSATIONS / 'CHANGELOG.md',
        gen           = GEN / CHAT_EXPORTS,
        input         = REPO_PARENT / CHAT_EXPORTS,
        input_glob    = 'data-*/',
        subject_depth = 1,
        validate_cmd  = f'src/main/{CHAT_EXPORTS}/validate.sh --{CHAT_EXPORTS}',
    ),
    CODE_PROJECTS: Pipeline(
        schemas       = [SESSION],
        changelog     = RSC_SCHEMA / SESSION / 'CHANGELOG.md',
        gen           = GEN / CODE_PROJECTS,
        input         = REPO_PARENT / CODE_PROJECTS,
        input_glob    = '-Users-*/*.jsonl',
        subject_depth = 2,
        validate_cmd  = f'src/main/{CODE_PROJECTS}/RUNME.sh --{CODE_PROJECTS}',
    ),
    BROWSER_CAPTURES: Pipeline(
        schemas       = [APICONVERSATION],
        changelog     = RSC_SCHEMA / APICONVERSATION / 'CHANGELOG.md',
        gen           = GEN / BROWSER_CAPTURES,
        input         = REPO_PARENT / BROWSER_CAPTURES,
        input_glob    = 'data-*/*/',
        subject_depth = 2,
        validate_cmd  = f'src/main/{BROWSER_CAPTURES}/validate.sh --batches',
    ),
}
```

Adding a new pipeline would then require only a new `PIPELINES` entry and a schema
directory — no new functions.
