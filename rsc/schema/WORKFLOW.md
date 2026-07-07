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
src/main/browser-captures/claude/validate.sh --browser-capture ext/browser-captures/claude/<uuid>
src/main/chat-exports/validate.sh      --chat-export   ext/chat-exports/<batch>
src/main/code-projects/RUNME.sh        --code-project  ext/code-projects/<project>
```

(code-projects converts each `.jsonl` before validating, so its runnable unit is the
project RUNME; `validate.sh --code-project-session` takes the *gen/* session dir, not ext/.)

Read the validation log in `gen/<pipeline>/<subject>/validation/<schema>/vN.log`.

### 2. Create the new schema version

```bash
cp rsc/schema/<pipeline>/<schema>/vN.json rsc/schema/<pipeline>/<schema>/v{N+1}.json
```

Edit `v{N+1}.json` minimally — only the changes needed to pass the failing data.
Then **diff it against its parent and read the diff**:

```bash
diff rsc/schema/<pipeline>/<schema>/vN.json rsc/schema/<pipeline>/<schema>/v{N+1}.json
```

The diff IS the change: it should read as exactly what the CHANGELOG narrative
will say, and nothing else. Anything extra — re-escaped strings, re-indentation,
reordered keys — means the edit did more than the change, however it happened.

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
src/main/browser-captures/RUNME.sh --browser-captures ext/browser-captures/claude
src/main/chat-exports/RUNME.sh     --chat-exports     ext/chat-exports
src/main/code-projects/RUNME.sh    --code-projects    ext/code-projects
```

Validation itself renders each datum's machine-local validation matrix — a `matrix.md`
in the datum's directory under `gen/`, beside its `validation/` logs, written by
`validate_versions.py` via the shared renderer `src/validation_matrix.py` whenever
the logs change, so it can never lag them. Git-ignored, because which data sits on which
machine is a local fact; the committed CHANGELOG.md beside the schema records only the
version *narrative*. To view the aggregate table across a pipeline's data (or re-render
without revalidating, e.g. after a renderer format change):

```bash
src/run_python_script.sh src/test/gen_changelog_matrix.py --pipeline <pipeline> [--write]
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

5. **Verify pointers and version currency** by running:

   ```bash
   src/test/pre_commit.sh   # check_schema_join: pointer validity
                            # check_model_join_versions: stale version refs
   ```

### 5. Check _reference/mcp.json

`rsc/schema/_reference/mcp.json` is a snapshot of the MCP protocol spec used as the
`mcp_path` reference column in `model_join.csv`. It has no changelog or pipeline — it
is updated manually when the MCP protocol itself evolves.

The file's `description` field records the source URL, the commit it was taken from, and a
SHA256 of the upstream file at that point:

```text
... (as at https://github.com/.../commit/<hash>; upstream SHA256: <hex>)
```

`pre_commit` checks currency automatically (`check_mcp_schema`) by fetching the raw schema
URL from the description and comparing its SHA256 to the stored value. If the upstream file
has changed, the check fails.

If `check_mcp_schema` fails: download the updated schema, convert it to Draft-04 if needed,
update the `description` field with the new commit URL and SHA256, then re-run `pre_commit`
to verify all `model_join.csv` pointers still resolve.

### 6. Update model.json if needed

`rsc/schema/model.json` is a hand-curated cross-pipeline type reference. After schema
changes, regenerate the candidates:

```bash
src/main/model/gen_model.sh
```

Review `gen/model/` for new or changed definitions and update `model.json` if any
cross-pipeline types need documenting. Also bump any stale version references in the
`default` section of `model.json`.

### 7. Run pre_commit

```bash
src/test/pre_commit.sh
git diff --cached src/test/pre_commit.log
```

All checks should pass. The diff to `pre_commit.log` is the final record of what changed.
Update `src/test/pre_commit_expected_score` if a tier's check count changed — its first
line is the combined code+schema total (matching the score in the log's head line),
followed by `code:` and `schema:` tier lines only; the `data` tier subtotal is
machine-local and never recorded.

---

## Notes from schema development in practice

### Coupled schema changes (v8 / v2)

When real MCP tool calls appeared in claude.ai (May 2026), both `conversations/v8` and
`apiConversation/v2` required the same relaxations — `approval_options`, `approval_key`,
`mcp_server_url`, and `IntegrationName` — because both schemas describe the same underlying
conversation data from different export angles. The coupling was only visible in
`model_join.csv`. Doing one without the other would have left the un-updated pipeline's
latest export failing every version — an all-`✗` row in that pipeline's matrix.

### Matrices are co-located with their data — there is nothing to prune

Each datum's `matrix.md` sits beside the `validation/` logs it summarises, inside the
datum's own `gen/` directory. The pipeline wipes and regenerates that directory per run,
matrix included, and deleting a datum deletes its matrix with it — so stale rows for
departed data cannot exist, and the old `--prune` step is gone. The matrix is purely
derived state; `check_pipeline_validation_outputs` verifies it agrees with the logs
(`matrix.current`) and that every input datum was processed at all.

### The two coverage gates: `check_pipeline_coverage` and `check_pipeline_frontier`

An earlier single check (`check_pipeline_latest_passing`) demanded that *every* entry pass the
*latest* schema version. That conflated two data models — re-fetchable captures
(browser-captures), always current because the pipeline re-pulls them, and immutable
point-in-time bulk-export snapshots (chat-exports), which legitimately rest at whatever version
matched when they were taken. Forcing an old snapshot to pass a newer schema is meaningless, and
it forced needless pruning of history (e.g. the pre-`approval_key_legacy` exports dropped at
conversations v10). It was replaced by two independent gates:

- **`check_pipeline_coverage`** — every datum must validate against *some* version. A datum that
  validates against none is unmodelled drift: evolve the schema (or record why it is permanently
  invalid). An old snapshot resting below the latest version is fine — a `✗` against a newer
  version is a fact, not an open issue.
- **`check_pipeline_frontier`** — the single *most recent* datum must validate against the
  *latest* version, so the schema frontier tracks the data frontier: no unmodelled newest export,
  and no version minted ahead of all data. Recency is pipeline-specific (`_datum_recency`):
  chat-exports uses the epoch in the batch dir name; browser-captures the capture's `updated_at`;
  code-projects the max record `timestamp` in the session `.jsonl`.

Together they catch a genuinely-drifting fresh export (it fails coverage *and* frontier) while
letting historical snapshots sit honestly below the latest version. `check_pipeline_validation_outputs`
still independently enforces that every entry is *registered* in the matrix and matches its `gen/` logs.
