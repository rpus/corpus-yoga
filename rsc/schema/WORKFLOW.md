# Schema change workflow

This document covers the end-to-end process for adding or changing a versioned schema.
Follow it in order. Pre-commit will catch most omissions, but `model_join.csv` review
(step 4) is a manual judgement call that automation cannot enforce.

A mint's data evidence - validation logs, observed values, the failing datum's
shape - comes from the usr room's runs; the build and its gate are hermetic. An
agent minting a version needs the evidence, never the corpus: what travels into
a PR is the anchored observation, not the data it observes.

---

## When to create a new version

Create `vN+1.json` (copy of `vN.json`) when the schema change is:

- **Relaxed** — allows values previously rejected (new field, widened type, optional → present)
- **Restricted** — rejects values previously accepted (tightened type, new required field)

Purely **refactored** changes (no validation effect) can go directly into the current version;
document them in the CHANGELOG narrative under `#### Refactored`, naming the vintage in prose.

That entry goes under the heading of **the version you amended** — the one whose file you
edited, which is not always the newest. An in-place edit spanning two versions is filed once,
under the newer of them, and names both. The sections run newest-first, so appending to the
end of the file files the note under the *oldest* version instead: done wrongly in three of
five families during the 2026-07-23 re-rooting, and caught only by checking placement
afterwards. Some families pre-seed the section with `None.`; fill that rather than adding a
second `#### Refactored` under the same version. The `RichLink.source` entry in
`rsc/schema/chat-exports/conversations/CHANGELOG.md` is the worked precedent: what changed,
in which versions, "No validation effect", and what was deliberately left untouched.

If a new export or capture fails validation against the current latest version, that is the
signal to create a new version. Run the item-level validate command from the `corpus-yoga test run` fix
hints to see the exact error before changing the schema.

---

## What here is live text, and what is frozen

This directory holds two kinds of prose, and they take opposite treatment when the world
moves under them — a root migration, a renamed tier, a retired command:

- **Never edited: validating content, in any version.** Enums, required fields, types — a
  superseded version must keep accepting and rejecting exactly what it did, or the vintage
  it records stops being a fact. This is why the `RichLink.source` anonymisation left the
  closed site enums of v11 and earlier untouched while rewording the descriptions above them.
- **Frozen by intent: CHANGELOG version entries.** "stages to cache/dashboard and promotes to
  output/dashboard/. Minted 2026-07-10" is a true sentence about 2026-07-10 and a false one
  about today; correcting it would falsify the record the entry exists to keep.
- **Live: the CHANGELOG preamble and the current version's `description` fields.** The
  preamble above the version history (the shared "each datum directory under `tmp/cache/`
  carries a `matrix.md`" line) and the current descriptions state present mechanics, so a
  stale one is simply wrong. Correcting it is `#### Refactored` work per the rule above.
- **Judgement: a superseded version's prose.** Precedent runs both ways. `RichLink.source`
  was reworded in place across v12 and v13 because a repo-wide policy — anonymisation once
  the user-specific matrices moved out of the repo — made the old text wrong to keep
  standing. The 2026-07-23 re-rooting did the opposite, leaving superseded descriptions
  naming pre-migration roots as the record of their vintage. The question to ask is whether
  the old text is *misleading* or merely *dated*: a path that has moved is dated, and a
  sentence that would now leak or deceive is misleading.

This distinction carries weight because **this directory is excluded from automated path
sweeps** — the four-root migration held it in `SWEEP_SKIP_PREFIXES`, rightly, since a sweep
cannot tell a frozen sentence from a live one. The cost is that the live half must be updated
by hand and nothing will remind you: that migration left this file's own commands naming an
`input/` root that no longer existed, and the six broken invocations were found by reading,
not by any check.

When writing a CHANGELOG entry about a path that has moved or gone, **do not quote the old
path as a code span**. `xref` reads a backticked path as a live reference, finds it missing,
and the gate vetoes the commit. Describe the change instead — "gained the `data/` root (now
`data/output/dashboard/…`)" rather than the old path in backticks beside the new one.

---

## Naming a new family

Family names carry type information — the number is the shape, not a style
accident: a **plural** family validates an *array of units* (`conversations`:
the bulk export's whole array), a **singular** family validates *one unit*
(`apiConversation`, `sessionConversation`, `markdownConversation`, `session`,
`projectMemory`). Read `users` as "the array the export's users.json holds",
`sessionConversation` as "one conversation projected from one session".

## Step-by-step

### 1. Identify the failure

```bash
src/main/pipeline/browser-captures/claude/validate.sh --browser-capture data/input/claude/chat/browser-API/<uuid>
src/main/pipeline/chat-exports/validate.sh      --chat-export   data/input/claude/chat/bulk-export/<batch>
src/main/pipeline/code-agents/run.sh        --code-agent  data/input/claude/code/machine-transport/<machine>/<project>
```

(code-agents converts each `.jsonl` before validating, so its runnable unit is the
project run.sh; `validate.sh --code-agent-session` takes the *tmp/cache/* session dir, not data/input/.)

Read the validation log in `tmp/cache/<pipeline>/<subject>/validation/<schema>/vN.log`.

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
src/run_python_script.sh src/test/dev/repairs/structure.bfs_order.py rsc/schema/<pipeline>/<schema>/v{N+1}.json
```

Then run all diagnostics to catch principle violations:

```bash
src/test/dev/run.sh   # will flag failing diagnostics in check_versioned_schema_diagnostics
```

### 3. Validate and register

Re-run the pipeline to generate validation logs for the new version:

```bash
src/main/pipeline/browser-captures/run.sh --browser-api data/input/claude/chat/browser-API
src/main/pipeline/chat-exports/run.sh     --chat-exports     data/input/claude/chat/bulk-export
src/main/pipeline/code-agents/run.sh    --code-agents    data/input/claude/code/machine-transport
```

Validation itself renders each datum's machine-local validation matrix — a `matrix.md`
in the datum's directory under `tmp/cache/`, beside its `validation/` logs, written by
`validate_versions.py` via the shared renderer `src/validation_matrix.py` whenever
the logs change, so it can never lag them. Git-ignored, because which data sits on which
machine is a local fact; the committed CHANGELOG.md beside the schema records only the
version *narrative*. To view the aggregate table across a pipeline's data (or re-render
without revalidating, e.g. after a renderer format change):

```bash
src/run_python_script.sh src/test/dev/gen_changelog_matrix.py --pipeline <pipeline> [--write]
```

Add a `## v{N+1}` narrative section to the CHANGELOG: intro narrative first, then a
single `### Replaces` heading whose body links the predecessor — `[v<N>.json](./v<N>.json)`
— then the change categories nested under it as constant-titled h4s: `#### Restricted`,
`#### Relaxed`, `#### Refactored`. State which data it now validates. (The Replaces
link is also what keeps xref's unreferenced inventory constant across mints: every
non-latest version file is referenced by its successor's section, so only each
family's frontier version is unreferenced — a mint costs `xref_expected_score`
no edit.)

`Restricted` / `Relaxed` / `Refactored` are the PR template's fractures / features /
fixes - semver's major / minor / patch: what vN admitted and v{N+1} rejects; what
vN rejected and v{N+1} admits; no validation effect. A new REQUIRED field is one Restricted entry (ruling 2026-07-12, the
thinking_hidden mint). Versions are observations of eras: new-era data is data
vN "now happens to reject", never data vN "rejected".

For a Restriction, also state its **materiality**: material means some observed
datum that passed vN fails v{N+1} — name what is excluded and where it rests;
non-material means every observed datum passes both, and the tightening bites
only futures — mark the section `#### Restricted (non-material)` and
say what would now fail by name. A closed enum minted from a survey is the
typical non-material case (session v9, `ModelId`: no observed record excluded;
a new model id now fails loudly instead of sliding through a bare string). The
distinction tells a reader whether upgrading re-classifies any existing data or
only sharpens the frontier.

### 4. Review model_join.csv  ← **do not skip**

Machines now hold part of this step: `identical`/`snake_cased` edges are re-verified
structurally and falsified ones FAIL every `corpus-yoga model` / pipeline run, as do
always-null claims the corpus has outgrown (`rsc/schema/model_join_kinds.csv` states
each kind's claim class and who re-verifies it). What stays yours is what no scan can
do: recognizing cross-NAME counterparts, judging relationships, and the coupling
foresight of step 3 below.

Whose duty (the maintainer's ruling, 2026-08-24): the assistant performs this
review at every schema mint as a matter of course - machine-checkable drift is
proposed by the machine, judgment cells are proposed by the assistant, and the
maintainer vets the proposals in the PR. A mint whose PR carries no join
review is incomplete.

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
   src/test/dev/run.sh   # check_schema_join: pointer validity (family dirs → latest version)
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

`corpus-yoga test run` checks currency automatically (`check_mcp_schema`) by fetching the raw
schema URL from the LATEST version's description and comparing its SHA256 to the
stored value. If the upstream file has changed, the check fails.

If `check_mcp_schema` fails: MINT the next version — download the updated schema,
convert it to Draft-04 if needed, set its `description` to the new commit URL and
SHA256, narrate the upstream change in the family CHANGELOG, and leave the old
snapshot in place (its history is data; the old update-in-place remedy destroyed
it). Then re-run `corpus-yoga test run` to verify all `model_join.csv` pointers still resolve
against the new latest.

### 6. Dispose the model.json obligations

`rsc/schema/model.json` is the hand-curated cross-family type reference, under the
`curate` disposal discipline (issue #19; rsc/CALCULUS.md) as TWO loops with different
pressure, both computed by `src/main/model/model_curation.py` from committed files only:

- **leisurely, advisory → `model_join.csv`**: the naive name scan (definition names in
  ≥2 families' latest versions) surfaces SHARED NAMES — the question, of which
  `name_collision` (the false friend) is one possible answer — and `corpus-yoga model sync`
  renders them pre-filled at `tmp/cache/model/shared_name_candidates.csv` (path cells
  computed; `identical` proposed where the shapes are structurally equal, editable);
  a human disposes each by pasting the row into `model_join.csv` with its
  `relationship` kind, so an "ignore" is a row too and zero means disposed. The kinds
  are declared data — `rsc/schema/model_join_kinds.csv`, each with its claim class —
  and the gate holds every row to them (`model.join_kind_declared`). Anyone, anytime,
  no gate pressure on the disposals themselves.
- **blocking, gated `model_join` ↔ `model.json`**: an edge whose kind asserts one shared
  type (`identical`, `snake_cased`) obligates `model.json` — the type is DOCUMENTED
  there or REJECTED with a reason in `rsc/schema/model_rejected.txt` — and every
  documented type must be grounded by such an edge (no orphan documentation).
  `check_model_obligations` gates both directions of the one grounding relation (by
  containing-definition name, or by property trail for inline field types like the
  account uuid), so the invariant is an equality: model.json documents exactly the
  shared types model_join asserts, minus rejections. An undocumented asserted identity —
  or a documented type no edge asserts — is a defect, not a queue.

After schema changes:

```bash
corpus-yoga model sync   # regenerate the per-schema catalogues (the review aid)
corpus-yoga model        # both loops in numbers: obligations (gating) and unrecorded collisions
```

This step is falsifiable, not "if needed". Occurrence paths use the de-versioned
family-dir grammar (`chat-exports/conversations`, resolved against the family's latest
version — `model_join.csv`'s grammar), and `check_model_occurrences` gates both the
grammar and that every instance pointer still resolves — a mint that renames a
documented field fails there, the review prompt.

### 7. Run `corpus-yoga test run`

```bash
src/test/dev/run.sh
git diff rsc/test/run.log
```

All checks should pass. The diff to `run.log` is the final record of what
changed — read it in the worktree, and stage it yourself when it says what you meant.
Nothing stages on your behalf.
Update `rsc/test/run_expected_checks` only if you WROTE or REMOVED a check — it
lists the check types the code and schema tiers run, one per line. Adding a schema version
multiplies invocations of existing checks and adds no check, so this file does not move for
it. A name that stops running, or a name that runs and is not listed, fails the gate.

---
