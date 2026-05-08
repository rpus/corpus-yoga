---
schema_file: rsc/schema/apiConversation/v1.json
principles_file: rsc/schema/apiConversation/principles.md
workflow_file: rsc/schema/apiConversation/workflow.md
version: "1.0"
---

# Schema Development Workflow for `rsc/schema/apiConversation/v{N}.json`

A living document describing how to maintain and extend the live API conversation schema.
Follows the same philosophy as `rsc/schema/conversations/workflow.md`.

---

## Lifecycle

API conversation data is captured on demand via Safari automation — it does not update
automatically. A new capture batch is needed to validate schema changes or incorporate
new API response shapes.

---

## Incorporating a new batch of captures

1. Fetch API JSON for the batch:

   ```bash
   src/main/browser-captures/safari_fetch_api_json.sh --captures ../browser-captures/data-<...>
   ```

2. Validate against the current schema:

   ```bash
   src/main/browser-captures/validate.sh --batches ../browser-captures
   ```

3. If any captures fail, update `v1.json` to accommodate the new shape (following
   the principles in `principles.md` and `rsc/schema/conversations/principles.md`).
4. Update `CHANGELOG.md`:

   ```bash
   src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline browser-captures --write
   ```

5. Run `src/test/pre_commit.sh` and confirm all checks pass.

---

## Creating a new schema version

Schema versions follow the same semantic versioning rules as `rsc/schema/conversations/`:

| Component | Trigger |
| --- | --- |
| **MAJOR** | A currently-passing capture now fails |
| **MINOR** | New API shapes supported; more captures pass |
| **PATCH** | Refactoring; no validation effect |

When cutting a new version:

1. Copy `v1.json` to `v{N}.json` and make the required changes.
2. Validate all captures against both the old and new version.
3. Add a new `## v{N}` section to `CHANGELOG.md` with **Relaxed**, **Restricted**,
   and/or **Refactored** subsections as appropriate.
4. Update the matrix table via `gen_changelog_matrix.py --write`.
5. Run `src/test/pre_commit.sh`.
