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

- **Single mooring** (lean, to confirm at review): `data/` is ONE symlink to an
  iCloud parent that itself contains `input/` and `output/`. The medium-side
  `mkdir data && mv input output data/` happens ONCE (shared medium, first
  room to apply); each room then replaces its two moorings with one.
- **The swap space cannot be `tmp/` this time** — `tmp/` is becoming a real
  tier. The swap is `swap/` at the root, gitignored transitionally with a rule
  that states its own deletion condition (the PR#11 pattern).

This directory is scaffolding, not product: **dismantle it once both rooms
have applied** (deletion keeps it reachable through history — this file is
itself proof, resurrected from `abaa4a5^` for its second service). The
dismantling commit removes, together:

- `src/restructure/` whole, rehearsal records included;
- the `.gitignore` transitional rules that name their own deletion here:
  `/swap`, and the four OLD-root rules (`/input /cache /output /logs`) kept
  only because a machine between merge and apply honestly holds both
  layouts — and the xref scan's skip-roots derive from `.gitignore`, so
  without them the not-yet-moved corpus floods the gate.

## Deltas from the first service (per script, the adaptation plan)

| script | first service | this service |
| --- | --- | --- |
| `common.py` | `MARKDOWN_MAP` (content paths changed) | `ROOT_MAP` (only roots change; the markdown content map is IDENTITY — corpus bytes must survive unmoved) |
| `gen_moves.py` | per-file typing into provider/channel/capture | whole-root claims + the mount extraction + the two script moves; totality check unchanged (every file claimed once or named excluded) |
| `gen_refs.py` | review aid for a done-by-hand sweep | THE sweep is bigger this time (`input/ output/ cache/ logs/` literals across code, docs, csvs — `rsc/cache_io.csv`, `rsc/cli/help.csv` prose, `.gitignore` anchors); still generated per-checkout, applied on this branch, reviewed by row |
| `build_harness.py` | seeded new-style roots into the worktree | same, under `data/`/`tmp/`; the `ext/` mount is pointed at the real harness root read-only (capture stays untested in rehearsal — it would write the real store) |
| `compare_outputs.py` | byte-identical modulo `MARKDOWN_MAP` | byte-identical, full stop (identity map): the corpus must not notice the move |
| `apply_moves.py` | shared-medium-once + per-room symlinks | same semantics; adds the mooring swap (two links → one `data/` link); nothing here touches shell config |

Post-migration follow-up (a separate arc, deliberately AFTER): the tier
redirection contract re-applies over the new layout and SIMPLIFIES — parents
are the honest redirect granularity, so five vars become three:
`YOGA_DATA=`, `YOGA_TMP=` (+ `YOGA_VENV=`); a full sandbox is one line.

## The recipe (per room)

    # from the room's MAIN checkout (old layout), with this branch in a worktree:
    git worktree add swap/dryrun root-taxonomy
    mkdir -p swap/reports

    # 1. generate this room's manifest from its real landscape
    python3 swap/dryrun/src/restructure/gen_moves.py --from . --swap swap \
        2>&1 | tee swap/reports/gen_moves.log

    # 2. review: swap/moves.csv is the plan; swap/view/ is the plan rendered
    python3 swap/dryrun/src/restructure/gen_refs.py --from .

    # 3. dry-run the migrated code against the future layout
    python3 swap/dryrun/src/restructure/build_harness.py --from . --moves swap/moves.csv \
        2>&1 | tee swap/reports/harness.log
    ( cd swap/dryrun && ./src/RUNME.sh )               # note the new home
    python3 swap/dryrun/src/restructure/compare_outputs.py --from . --worktree swap/dryrun \
        2>&1 | tee swap/reports/equivalence.log        # identity map: byte-identical or bust

    # 4. commit the room's rehearsal record (the merge decision must be
    #    reproducible from the repo, not from anyone's terminal): write
    #    src/restructure/rehearsals/<room>-<date>.md containing the room's
    #    moves.csv verbatim + totality line, the compare_outputs summary with
    #    an explanation for every residual finding, and the apply dry-run
    #    plan. Name the room and date in the text — no indexicals. The
    #    records are deleted with this whole directory after both rooms
    #    apply; history keeps them reachable.

    # 5. when satisfied, execute (--apply is the point of no return; without it, a plan prints)
    python3 swap/dryrun/src/restructure/apply_moves.py --from . --moves swap/moves.csv \
        2>&1 | tee swap/reports/apply-plan.log
    python3 swap/dryrun/src/restructure/apply_moves.py --from . --moves swap/moves.csv --apply

Whichever room applies first also performs the one shared-medium move
(`mkdir data && mv input output data/` on iCloud); the second room's apply
finds it `done` (absence of work is a signal, not an error) and performs only
its local share: the single `data/` mooring, the `tmp/` locals, and the
`ext/claude-code-projects` mount. Disposals go to `swap/disposed/`, never
deleted. Every report lands under `swap/` — one folder tells the room's whole
story.
