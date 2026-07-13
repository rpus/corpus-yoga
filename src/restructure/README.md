# The restructure machinery (temporary; delete after the merge)

Tools for migrating the data roots to the corpus type system —
`input/<provider>/<channel>/<capture>/` and `output/markdown/<provider>/<channel>/`
— by manifest: generate the moves as data, view them as a symlink tree, dry-run
the migrated code against them in a worktree, compare outputs for equivalence,
then execute for real. Every step is per-room: each machine generates its own
manifest from its own landscape, so a room's local wrinkles (stray files, absent
optional roots) surface as manifest rows, not surprises.

This directory is scaffolding, not product: **delete it after `restructure`
merges** (deleting post-merge keeps it reachable through history even if the
branch itself is deleted).

## The pieces

| script | role |
| --- | --- |
| [gen_moves.py](src/restructure/gen_moves.py) | scan the OLD-layout data roots → `moves.csv` (the one authority) + a browsable symlink `view/` + a totality check (every file claimed exactly once or named excluded) |
| [gen_refs.py](src/restructure/gen_refs.py) | scan an OLD-layout checkout's committed files → `refs.csv`, the code-side reference manifest (mechanical vs judgment sites) — review aid, already applied on this branch |
| [build_harness.py](src/restructure/build_harness.py) | materialize dry-run data roots in THIS checkout from `moves.csv`: new-style `input/` symlinks, empty `cache/`, precious `output/` tiers copied in (summary deposits included — they are deposits, not dressing) |
| [compare_outputs.py](src/restructure/compare_outputs.py) | equivalence verdict: old `output/markdown` vs rebuilt, byte-identical modulo the declared path map; seeded tiers must be untouched |
| [apply_moves.py](src/restructure/apply_moves.py) | execute `moves.csv` against the real roots — dry-run by default, `--apply` to write; iCloud-side moves happen once (shared medium), the per-room symlink boundary each room applies itself |
| [common.py](src/restructure/common.py) | the shared vocabulary: the markdown path map, manifest I/O |

## The recipe (per room)

```bash
# from the room's MAIN checkout (old layout), with this branch in a worktree:
git worktree add tmp/restructure/dryrun restructure
mkdir -p tmp/restructure/reports

# 1. generate this room's manifest from its real landscape
python3 tmp/restructure/dryrun/src/restructure/gen_moves.py --from . --swap tmp/restructure \
    2>&1 | tee tmp/restructure/reports/gen_moves.log

# 2. review: tmp/restructure/moves.csv is the plan; tmp/restructure/view/ is the plan rendered
#    (optional review aid: the code-side manifest of an old-layout checkout)
python3 tmp/restructure/dryrun/src/restructure/gen_refs.py --from .

# 3. dry-run the migrated code against the future layout
python3 tmp/restructure/dryrun/src/restructure/build_harness.py --from . --moves tmp/restructure/moves.csv \
    2>&1 | tee tmp/restructure/reports/harness.log
( cd tmp/restructure/dryrun && ./RUNME.sh )        # run once cold; a second run heals currency stamps
python3 tmp/restructure/dryrun/src/restructure/compare_outputs.py --from . --worktree tmp/restructure/dryrun \
    2>&1 | tee tmp/restructure/reports/equivalence.log
# expected residue, one line about index.md: MISSING (the recipe does not rebuild
# the book index) — or DIFFERS if you optionally run `./yoga indexing build` in
# the worktree first (fresh index vs the OLD corpus's stale one). Either reading
# convicts the stale old index, not the rebuild; it clears post-migration.

# 4. when satisfied, execute (the point of no return is --apply; without it, a plan prints)
python3 tmp/restructure/dryrun/src/restructure/apply_moves.py --from . --moves tmp/restructure/moves.csv \
    2>&1 | tee tmp/restructure/reports/apply-plan.log                                                     # plan
python3 tmp/restructure/dryrun/src/restructure/apply_moves.py --from . --moves tmp/restructure/moves.csv --apply  # execute
```

Whichever room applies first also restructures the shared iCloud trees; the
second room's apply then finds those moves already done (reported as `done`,
skipped — absence of work is a signal, not an error) and performs only its
local share: the symlink boundary (`input/claude`, `input/gemini`,
`input/claude-code-projects`) and any room-local data.

Disposals (`dispose` rows — e.g. stray scrape logs) are MOVED to
`<swap>/disposed/`, never deleted: inspect at leisure, delete by hand.

Every report lands under `tmp/restructure/` — `moves.csv`, the teed `reports` logs, and
the worktree's own `logs/RUNME/<ts>.log` (pipeline runs) and
`logs/src/test/pre_commit.log` (the full gate report incl. the machine-local
data tier) — one folder tells the room's whole story.
