# Rehearsal record — reading-room, 2026-07-23

Follow-up to [home-room-2026-07-22-clean.md](./home-room-2026-07-22-clean.md).
Reading-room's rehearsal of the four-root taxonomy against `root-taxonomy` at `09f1abd`,
following the recipe steps 0–5 in order. **The equivalence bar is met: byte-identical,
nothing to explain.**

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

Reading-room's mooring topology matches home-room's: `input/claude`, `input/gemini`,
`output` are symlink moorings (the `data` rows); `cache`, `logs` are real dirs (the
`local` rows); `input/claude-code-projects` is the mount.

## The equivalence verdict — clean

    markdown: 349 byte-identical, 0 differ, 0 missing, 0 extra
    artifacts: stable
    dashboard: stable
    indexing: stable
    memories: stable
    serve_markdown: stable

Zero residuals, zero explanations. The corpus does not notice the move.

The file count is 349 rather than the 545 of home-room's 2026-07-22 record because the
196 twin deposits have since been purged (PRs #21/#23/#24): the store now holds 103
summary deposits, not 299, and `yoga summaries` reports no twins.

## The two-pass finding

The bar is met **after a second worktree pass**. A single pass leaves all 100
`claude/chat/conversations/*.md` differing in exactly two frontmatter lines:

    cross_checked_against: data-…-1784702804-…-batch-0000   →   none
    currency: in-sync                                       →   unchecked

`build_harness` seeds `tmp/` empty, so on the first pass the browser-captures pipeline
projects the conversations *before* chat-exports has atomised any batch — there is
nothing to cross-check against. The second pass runs against the now-warm
`tmp/cache/chat-exports` and records the batch. The real store's cache is warm from
ordinary use, which is why only the worktree side shows it.

Recipe step 3 prescribes a single `./src/RUNME.sh`; two are required from a cold cache.
Home-room's 2026-07-22 record already says "two full worktree passes", so this was known
practice that the recipe does not state.

## The apply plan (dry run — NOT executed)

    3 move(s) to perform: {'mount': 1, 'local': 2} — nothing moves on the medium
      LINK data -> ~/Documents/dev/com/github/rpus/claude-export-yoga
      LINK ext/claude-code-projects -> ~/.claude/projects
      UNLINK input/claude (old mooring, subsumed by data/)
      UNLINK input/gemini (old mooring, subsumed by data/)
      UNLINK output (old mooring, subsumed by data/)
    dry run (pass --apply to perform)

The medium is untouched: `data/` moors to the existing iCloud parent, which already
contains `input/` and `output/`. Everything remaining is local — the mooring, the `ext/`
mount re-hang, `cache/`+`logs/` under `tmp/`, and the subsumed moorings unlinked.

## Recipe fixes confirmed working

The three gaps reported on PR #20 are closed, verified in this run rather than by reading
the diff:

- `gen_refs` wrote `refs.csv` to `swap/refs.csv`; the repo root stayed clean, so no
  `yoga check` was poisoned.
- The record step now follows the apply dry-run, so it can quote the plan it must contain.
- Step 5 states both routes for the xref count; this record takes the header-link route.

## Status

Manifest totality OK; equivalence byte-identical with nothing to explain; apply plan clean
and all-local. Reading-room's rehearsal obligations are complete.
