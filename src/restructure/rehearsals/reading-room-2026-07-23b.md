# Rehearsal record — reading-room, 2026-07-23 (second run, recipe followed as written)

Follow-up to [reading-room-2026-07-23.md](./reading-room-2026-07-23.md). That earlier
record was produced against `09f1abd` under the superseded recipe, and its step 5 was
forced through with `--no-verify`; it reported results but did not execute the recipe.
This run executes the current recipe against `ab816c2`, every step as written, no bypass.

## The manifest (totality OK)

    old,new,rule
    input/claude,data/input/claude,data
    input/claude-code-projects,ext/claude-code-projects,mount
    input/gemini,data/input/gemini,data
    output,data/output,data
    cache,tmp/cache,local
    logs,tmp/logs,local
    RUNME.sh,src/RUNME.sh,"excluded: git-tracked — moves with the branch, not with apply"
    PREREQUISITES.sh,src/PREREQUISITES.sh,"excluded: git-tracked — moves with the branch, not with apply"

    totality: OK — every root entry claimed exactly once

Reading-room's moorings are `input/claude`, `input/gemini`, `output` (the `data` rows);
`cache` and `logs` are real dirs (the `local` rows); `input/claude-code-projects` is the
mount.

## The equivalence verdict — clean

    markdown: 349 byte-identical, 0 differ, 0 missing, 0 extra
    artifacts: stable
    dashboard: stable
    indexing: stable
    memories: stable
    serve_markdown: stable

Zero residuals, nothing to explain. Reached by running step 3's two passes as the recipe
prescribes them, rather than by discovering the requirement mid-run: `build_harness` seeds
`tmp/` empty, pass 1 projects before anything is atomised to cross-check against, pass 2
records the batch against the warmed `tmp/cache`.

## The apply plan (dry run — NOT executed)

    3 move(s) to perform: {'mount': 1, 'local': 2} — nothing moves on the medium
      LINK data -> ~/Documents/dev/com/github/rpus/claude-export-yoga
      LINK ext/claude-code-projects -> ~/.claude/projects
      UNLINK input/claude (old mooring, subsumed by data/)
      UNLINK input/gemini (old mooring, subsumed by data/)
      UNLINK output (old mooring, subsumed by data/)
    dry run (pass --apply to perform)

The medium is untouched: `data/` moors to the iCloud parent that already holds `input/`
and `output/`. What remains is local — the mooring, the `ext/` mount re-hang, `cache/` and
`logs/` under `tmp/`, and the subsumed moorings unlinked.

## What this run establishes, and what it does not

Establishes: the recipe is executable end to end by a room that has not written it. Every
step ran as printed — `refs.csv` under `swap/` leaving the repo root clean, two passes,
the record step following the dry-run it quotes, and this commit passing the gate on its
own merits under the self-gating hook (#25), with no `--no-verify`.

Does not establish: that the apply works. `--apply` has still never been executed by
either room, and no machine has yet run `yoga` against genuinely moved roots. What is
proven is that the migrated code rebuilds the corpus byte-identically from a harness that
fabricates the new layout — not that the apply builds that layout correctly on a real
landscape.

## Status

Manifest totality OK; equivalence byte-identical; apply plan clean and all-local; recipe
followed without deviation. Reading-room's rehearsal obligations are complete.
