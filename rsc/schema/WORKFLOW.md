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
src/main/code-agents/RUNME.sh        --code-agent  ext/code-agents/<room>/<project>
```

(code-agents converts each `.jsonl` before validating, so its runnable unit is the
project RUNME; `validate.sh --code-agent-session` takes the *gen/* session dir, not ext/.)

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
src/main/code-agents/RUNME.sh    --code-agents    ext/code-agents
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

Narrate temporally, and classify only the fate of PREVIOUSLY-VALID data
(ruling 2026-07-12, the thinking_hidden mint): every mint admits its
triggering datum — that is the mint's reason for existing, told in the intro
narrative, never a `Relaxed` entry — so a new REQUIRED field is ONE
Restricted entry. And versions are observations of eras: old vN modelled
everything its era showed and rejected nothing in its lifetime — new-era
data is data vN "now happens to reject", never data vN "rejected".

For a Restriction, also state its **materiality**: material means some observed
datum that passed vN fails v{N+1} — name what is excluded and where it rests;
non-material means every observed datum passes both, and the tightening bites
only futures — mark the section `### Restricted since vN (non-material)` and
say what would now fail by name. A closed enum minted from a survey is the
typical non-material case (session v9, `ModelId`: no observed record excluded;
a new model id now fails loudly instead of sliding through a bare string). The
distinction tells a reader whether upgrading re-classifies any existing data or
only sharpens the frontier.

### 4. Review model_join.csv  ← **do not skip**

Open `rsc/schema/model_join.csv` and:

1. **Pointers name no versions** — every cell is a versioned FAMILY DIR relative
   to `rsc/schema` (`chat-exports/conversations#/definitions/…`,
   `code-agents/session#/definitions/…`, `browser-captures/apiConversation#/definitions/…`,
   `_reference/mcp#/definitions/…`). `check_schema_join`
   resolves family dirs against their LATEST version, so a mint costs this file
   no edit at all; if the mint renamed or removed a referenced definition, the
   pointer check fails — that failure IS the review prompt. (The old
   version-pinned grammar churned dozens of cells per mint, and its bare
   `vN.json#…` session cells contained neither "session" nor a pipeline name —
   invisible to search, which is how a 2026-07-10 review declared the file a
   no-op while 37 rows needed judgement. `check_model_join_versions` now rejects
   any reintroduced pin.)

2. **Update stale notes** — fields that were "always null in observed exports" or
   `null_in_api` may now have real values; correct the relationship and note columns.

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

5. **Verify pointers and grammar** by running:

   ```bash
   src/test/pre_commit.sh   # check_schema_join: pointer validity (family dirs → latest version)
                            # check_model_join_versions: no version-pinned cells
   ```

### 5. Check _reference/mcp

`rsc/schema/_reference/mcp/` is a versioned family of VERBATIM SNAPSHOTS of the MCP
protocol spec (converted to draft-04), used as the `mcp_path` reference column in
`model_join.csv` (`_reference/mcp#/definitions/…` — the same family-dir grammar as
every other column, resolved against the latest version). It enters no pipeline —
no data is validated against it — and the house style diagnostics deliberately
skip `_reference/` families: repairing upstream text to satisfy house rules would
falsify the snapshot. Its history lives in `rsc/schema/_reference/mcp/CHANGELOG.md`;
the first version is `rsc/schema/_reference/mcp/v1.json`.

Each version's `description` field records the source URL, the commit it was taken
from, and a SHA256 of the upstream file at that point:

```text
... (as at https://github.com/.../commit/<hash>; upstream SHA256: <hex>)
```

`pre_commit` checks currency automatically (`check_mcp_schema`) by fetching the raw
schema URL from the LATEST version's description and comparing its SHA256 to the
stored value. If the upstream file has changed, the check fails.

If `check_mcp_schema` fails: MINT the next version — download the updated schema,
convert it to Draft-04 if needed, set its `description` to the new commit URL and
SHA256, narrate the upstream change in the family CHANGELOG, and leave the old
snapshot in place (its history is data; the old update-in-place remedy destroyed
it). Then re-run `pre_commit` to verify all `model_join.csv` pointers still resolve
against the new latest.

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
  code-agents the max record `timestamp` in the session `.jsonl`.

Together they catch a genuinely-drifting fresh export (it fails coverage *and* frontier) while
letting historical snapshots sit honestly below the latest version. `check_pipeline_validation_outputs`
still independently enforces that every entry is *registered* in the matrix and matches its `gen/` logs.
