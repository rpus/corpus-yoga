# The restructure machinery, second service (temporary; delete after the merge)

Tools for migrating to the **four-root taxonomy** — each root exactly one
medium and ownership class, the sync table losing every footnote:

| root | holds | medium | ownership |
| --- | --- | --- | --- |
| `src/` + `rsc/` | machinery (now including `RUNME.sh`, `PREREQUISITES.sh`) | git | ours |
| `data/` | `input/` + `output/` | iCloud | ours — **no exceptions clause** |
| `tmp/` | `cache/` + `logs/` | local | ours, disposable |
| `ext/` | foreign mounts (first: `claude-code-projects` → `~/.claude/projects`) | machine-local symlinks | **not ours** — readable, expiring, never synced |

`ext/` is reborn with a sharpened meaning: the *register of foreign mounts* —
`ls ext/` answers "what outside state can this workspace read", the same
declared-not-implicit doctrine as `rsc/forge.csv` and `rsc/machine/machines.csv`.
The projects symlink moves there from `input/` because it is a live SOURCE, not
a capture — but stays a mount (not a code constant) because it is "r" not "x":
workspace text search greps uncaptured conversations through it. `data/` is
thereby pure medium: everything under it lives on iCloud, full stop.

The moves, whole-root and enumerable (unlike last time, no per-file typing):

    input/            → data/input/         (minus the claude-code-projects mount)
    output/           → data/output/
    cache/            → tmp/cache/
    logs/             → tmp/logs/
    input/claude-code-projects → ext/claude-code-projects
    RUNME.sh          → src/RUNME.sh
    PREREQUISITES.sh  → src/PREREQUISITES.sh

Two decisions carried into the manifest rather than left in anyone's head:

- **Single mooring, ZERO medium bytes moved** (the PR #20 review's
  simplification): the room's old moorings already point into one medium
  parent that already contains `input/` + `output/` — that parent simply IS
  the `data/` container. `data/` is ONE symlink to it (`data → <parent>`, not
  `<parent>/data`); nothing moves on the medium, ever, and there is no
  first-room/second-room medium step. `apply_moves` derives the parent from
  the room's own moorings (they must agree — SPLIT-MEDIUM refuses otherwise)
  and prints it ~-shortened. Because the link is additive, a room may
  PRE-MOOR `data/` (and `ext/claude-code-projects`) any time before the
  merge; apply then reports them `done`.
- **The swap space cannot be `tmp/` this time** — `tmp/` is becoming a real
  tier. The swap is `swap/` at the root, gitignored transitionally with a rule
  that states its own deletion condition (the PR#11 pattern).

Committed text, records, and printed plans write paths **~-shortened**, never
`/Users/<name>/…` — portable across rooms, no usernames in the repo.

This directory is scaffolding, not product: **dismantle it once both rooms
have applied** (deletion keeps it reachable through history — this file is
itself proof, resurrected from `abaa4a5^` for its second service). The
dismantling commit removes, together:

- `src/restructure/` whole, rehearsal records included;
- the `.gitignore` transitional rules that name their own deletion here:
  `/swap`, and the four OLD-root rules (`/input /cache /output /logs`) kept
  only because a machine between merge and apply honestly holds both
  layouts — and the xref scan's skip-roots derive from `.gitignore`, so
  without them the not-yet-moved corpus floods the gate;
- per machine, the vestige check those rules were HIDING (found in
  home-room by eye, 2026-07-23 — empty `input/` and `cache/` re-minted by
  pre-#26 stragglers sat invisible precisely because the transitional
  rules gitignored them): `rmdir input cache logs 2>/dev/null` — empty
  dirs only, `rmdir` refuses anything else — plus each machine's local
  `rm -rf swap`;
- the expectation files: deleting this directory and its five records
  changes the xref inventory and the check counts, so the dismantling
  commit updates `src/test/xref_expected_score` (and
  `pre_commit_expected_score` if counts move) in the same commit, per the
  gate's own remedies.

## Deltas from the first service (per script, the adaptation plan)

| script | first service | this service |
| --- | --- | --- |
| `common.py` | `MARKDOWN_MAP` (content paths changed) | `ROOT_MAP` (only roots change; the markdown content map is IDENTITY — corpus bytes must survive unmoved) |
| `gen_moves.py` | per-file typing into provider/channel/capture | whole-root claims + the mount extraction + the two script moves; totality check unchanged (every file claimed once or named excluded) |
| `gen_refs.py` | review aid for a done-by-hand sweep | THE sweep is bigger this time (`input/ output/ cache/ logs/` literals across code, docs, csvs — `rsc/cache_io.csv`, `rsc/cli/help.csv` prose, `.gitignore` anchors); still generated per-checkout, applied on this branch, reviewed by row |
| `build_harness.py` | seeded new-style roots into the worktree | same, under `data/`/`tmp/`; the `ext/` mount is pointed at the real harness root read-only (capture stays untested in rehearsal — it would write the real store) |
| `compare_outputs.py` | byte-identical modulo `MARKDOWN_MAP` | byte-identical, full stop (identity map): the corpus must not notice the move |
| `apply_moves.py` | shared-medium-once + per-room symlinks | ALL-LOCAL: the medium is never touched (data → the existing parent); links + two tmp/ moves + old-root retirement; nothing here touches shell config |

Post-migration follow-up (a separate arc, deliberately AFTER): the tier
redirection contract re-applies over the new layout and SIMPLIFIES — parents
are the honest redirect granularity, so five vars become three:
`YOGA_DATA=`, `YOGA_TMP=` (+ `YOGA_VENV=`); a full sandbox is one line.

## The recipe (per room)

    # 0. PREREQUISITE, from a checkout of CURRENT MAIN: bring the real corpus
    #    current with the code that will rebuild it in the worktree —
    ./yoga run
    #    Skipping this makes the comparer report stale-real differs that are
    #    main's lag, not the migration's doing (observed home-room 2026-07-22:
    #    index.md still carried a twice-retired verb name in its header).
    #    And do NOT run yoga run from THIS branch's checkout before applying:
    #    its code reads data/ and tmp/, which do not exist until apply — the
    #    run fails on arrival (also observed, same day).

    # from the room's MAIN checkout (old layout), with this branch in a worktree:
    git worktree add swap/dryrun root-taxonomy
    mkdir -p swap/reports

    # 1. generate this room's manifest from its real landscape
    python3 swap/dryrun/src/restructure/gen_moves.py --from . --swap swap \
        2>&1 | tee swap/reports/gen_moves.log

    # 2. review: swap/moves.csv is the plan; swap/view/ is the plan rendered.
    #    refs.csv lands under swap/ (gitignored) — NEVER at the repo root,
    #    where the next `yoga check` would scan its migration paths as
    #    hundreds of missing references and rewrite xref.csv into a failing
    #    state (found 2026-07-23, reading-room)
    python3 swap/dryrun/src/restructure/gen_refs.py --from . --swap swap

    # 3. dry-run the migrated code against the future layout — TWO passes:
    #    build_harness seeds tmp/ EMPTY (fresh-clone proof), so on pass 1
    #    browser-captures projects conversations before chat-exports has
    #    atomised anything to cross-check against, leaving every projection's
    #    cross_checked_against/currency frontmatter at none/unchecked. Pass 2
    #    runs against the warmed tmp/cache and records the batch; only then is
    #    the compare meaningful (home-room's records always ran two passes;
    #    the recipe said one — reading-room's 2026-07-23 rehearsal, defect 1).
    python3 swap/dryrun/src/restructure/build_harness.py --from . --moves swap/moves.csv \
        2>&1 | tee swap/reports/harness.log
    ( cd swap/dryrun && ./src/RUNME.sh && ./src/RUNME.sh )   # note the new home; twice
    python3 swap/dryrun/src/restructure/compare_outputs.py --from . --worktree swap/dryrun \
        2>&1 | tee swap/reports/equivalence.log        # identity map: byte-identical or bust

    # 4. dispose of the gate-born tmp/, then take the apply DRY RUN (the plan
    #    the record must quote): on a mid-transition checkout the branch's own
    #    gate runs have already created tmp/logs/, so apply's `logs ->
    #    tmp/logs` row reads CONFLICT and refuses (observed home-room
    #    2026-07-22, the five-state lattice working). Everything under the
    #    born-early tmp/ is disposable gate output:
    rm -rf tmp
    python3 swap/dryrun/src/restructure/apply_moves.py --from . --moves swap/moves.csv \
        2>&1 | tee swap/reports/apply-plan.log

    # 5. commit the room's rehearsal record (the merge decision must be
    #    reproducible from the repo, not from anyone's terminal): write
    #    src/restructure/rehearsals/<room>-<date>.md containing the room's
    #    moves.csv verbatim + totality line, the compare_outputs summary with
    #    an explanation for every residual finding, and step 4's apply
    #    dry-run plan. Name the room and date in the text — no indexicals;
    #    paths ~-shortened. The xref gate will count the new file, so EITHER
    #    open the record with a header link to the latest prior record —
    #    `Follow-up to [<prior>.md](./<prior>.md)` — which makes the prior
    #    referenced and nets the count to zero (the 2f59e89 pattern), OR, for
    #    a record with no prior to link, bump the last number in
    #    src/test/xref_expected_score by one (the f968325 pattern). The
    #    records are deleted with this whole directory after both rooms
    #    apply; history keeps them reachable.

    # 6. when satisfied, execute (--apply is the point of no return)
    python3 swap/dryrun/src/restructure/apply_moves.py --from . --moves swap/moves.csv --apply

Every step is per-room and LOCAL — there is no shared-medium step and no
ordering between the rooms. Each room's apply makes the single `data/`
mooring (or finds a pre-moored one `done`), re-hangs the
`ext/claude-code-projects` mount, moves its own `cache/`+`logs/` under
`tmp/`, and retires the old moorings and roots (removed only when empty;
residue reported, never destroyed). The corpus bytes on the medium are
untouched throughout. Every report lands under `swap/` — one folder tells
the room's whole story.
