# Schema change workflow

This document covers the end-to-end process for adding or changing a versioned schema.
Follow it in order. Pre-commit will catch most omissions, but `model_join.csv` review
(step 4) is a manual judgement call that automation cannot enforce.

---

## When to create a new version

Create `vN+1.json` (copy of `vN.json`) when the schema change is:

- **Relaxed** — allows values previously rejected (new field, widened type, optional → present)
- **Restricted** — rejects values previously accepted (tightened type, new required field)

Purely **refactored** changes (no validation effect) can go directly into the current version;
document them in the CHANGELOG narrative as `### Refactored since vN`.

If a new export or capture fails validation against the current latest version, that is the
signal to create a new version. Run the item-level validate command from the pre_commit fix
hints to see the exact error before changing the schema.

---

## Step-by-step

### 1. Identify the failure

```bash
src/main/browser-captures/validate.sh --browser-capture ext/browser-captures/<uuid>
src/main/chat-exports/validate.sh      --chat-export   ext/chat-exports/<batch>
src/main/code-projects/validate.sh     --code-project-session ext/code-projects/<project>/<uuid>
```

Read the validation log in `gen/<pipeline>/<subject>/validation/<schema>/vN.log`.

### 2. Create the new schema version

```bash
cp rsc/schema/<pipeline>/<schema>/vN.json rsc/schema/<pipeline>/<schema>/v{N+1}.json
```

Edit `v{N+1}.json` minimally — only the changes needed to pass the failing data.
Run the BFS order repair after editing:

```bash
src/run_python_script.sh src/test/repairs/structure.bfs_order.py rsc/schema/<pipeline>/<schema>/v{N+1}.json
```

Then run all diagnostics to catch principle violations:

```bash
src/test/pre_commit.sh   # will flag failing diagnostics in check_versioned_schema_diagnostics
```

### 3. Validate and register

Re-run the pipeline to generate validation logs for the new version:

```bash
src/main/browser-captures/RUNME.sh --browser-captures ext/browser-captures
src/main/chat-exports/RUNME.sh     --chat-exports     ext/chat-exports
src/main/code-projects/RUNME.sh    --code-projects    ext/code-projects
```

Register results in the CHANGELOG matrix:

```bash
src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline <pipeline> --write
```

If stale entries exist (data no longer on disk):

```bash
src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline <pipeline> --prune
```

Add a `## v{N+1}` narrative section to the CHANGELOG using the categories:
`### Restricted since vN`, `### Relaxed since vN`, `### Refactored since vN`.
State which data it now validates.

### 4. Review model_join.csv  ← **do not skip**

Open `rsc/schema/model_join.csv` and:

1. **Bump version references** — replace `v{N}.json` with `v{N+1}.json` in any rows
   that reference the schema you changed.

2. **Update stale notes** — fields that were "always null in observed exports" or
   `api_null` may now have real values; correct the relationship and note columns.

3. **Check for coupling** — look at every field you changed and ask:
   - Does the same field exist in another pipeline's schema?
   - Was it changed there too, or does it need to be?

   The `approval_options`, `approval_key`, `mcp_server_url`, and `IntegrationName`
   fields appeared in *both* `conversations` (v8) and `apiConversation` (v2) and required
   the same relaxation in the same upgrade cycle. This was visible in model_join.csv
   *after the fact* — the goal is to catch it *before* committing only one side.

4. **Add new rows** for any new definitions that have counterparts in other schemas.
   New tool types (`SearchMcpRegistryToolUseBlock`) and new message fields
   (`compaction_summary`) are examples.

5. **Verify pointers** by running:

   ```bash
   src/test/pre_commit.sh   # check_schema_join validates all JSON Pointer fragments
   ```

### 5. Check _reference/mcp.json

`rsc/schema/_reference/mcp.json` is a snapshot of the MCP protocol spec used as the
`mcp_path` reference column in `model_join.csv`. It has no changelog or pipeline — it
is updated manually when the MCP protocol itself evolves.

The file's `description` field records the source URL and the exact commit it was taken from:

```text
https://github.com/modelcontextprotocol/modelcontextprotocol/commit/<hash>
```

To check for newer versions:

```bash
# Compare current commit against latest on main
open https://github.com/modelcontextprotocol/modelcontextprotocol/commits/main/schema/2025-11-25/schema.json
```

If a newer commit exists, download the updated schema, convert it to Draft-04 if needed,
update the `description` field with the new source commit, and re-run `check_schema_join`
to verify all `model_join.csv` pointers still resolve.

As of 2026-05-20, the snapshot is current (commit `357adac`).

### 6. Update model.json if needed

`rsc/schema/model.json` is a hand-curated cross-pipeline type reference. After schema
changes, regenerate the candidates:

```bash
src/main/model/gen_model.sh
```

Review `gen/model/` for new or changed definitions and update `model.json` if any
cross-pipeline types need documenting. Also bump any stale version references in the
`default` section of `model.json`.

### 6. Run pre_commit

```bash
src/test/pre_commit.sh
git diff src/test/pre_commit.log
```

All checks should pass. The diff to `pre_commit.log` is the final record of what changed.
Update `src/test/pre_commit_expected_score` if the total count changed.

---

## Notes from schema development in practice

### Coupled schema changes (v8 / v2)

When real MCP tool calls appeared in claude.ai (May 2026), both `conversations/v8` and
`apiConversation/v2` required the same relaxations — `approval_options`, `approval_key`,
`mcp_server_url`, and `IntegrationName` — because both schemas describe the same underlying
conversation data from different export angles. The coupling was only visible in
`model_join.csv`. Doing one without the other would have left the `check_pipeline_latest_passing`
pre_commit check failing for whichever pipeline was not updated.

### `--prune` before `--write` for depth-2 schemas

For pipelines with `subject_depth = 2` (code-projects), always run `--prune` before
`--write` when data has been deleted or renamed. `--write` only appends; it never removes
stale rows. Stale rows cause `check_pipeline_latest_passing` failures that cannot be
resolved by running the pipeline.

### `gen_changelog_matrix --write` does not reorder existing rows

The tool appends new rows and updates existing ones in place. Row order in the CHANGELOG
reflects insertion order. Use `--prune` to remove stale rows cleanly; do not sort manually
unless making a deliberate one-off correction (which will produce a noisy diff).

### The `check_pipeline_latest_passing` check

Every entry in the CHANGELOG must pass validation against the *latest* schema version.
A `✗` recorded against an older version is historical fact; a `✗` against the latest
version is an open issue. There is intentionally no way to "accept" a current failure —
fix the schema or document why the data is permanently invalid.
