# TODO

## RUNME.sh output too large to scan for failures

Validation errors produce enormous output (400KB+). Running RUNME.sh and checking
only tail output will miss failures. pre_commit already surfaces pass/fail correctly;
consider whether RUNME.sh should emit a compact summary line per session in addition
to the full error output, so failures are visible without scrolling.

## Merge CLAUDE.md and README.md; use TODO as the live capture mechanism

CLAUDE.md and README.md serve the same audience and are diverging from each other and
from reality. Merge into one document that is the stable structural reference. Instead
of updating documentation in-place when something is discovered or changes, write it
to TODO. The human maintainer audits TODO (and commits) and decides what gets promoted
into the permanent doc, what gets acted on, and what gets discarded. Documentation
that isn't actively maintained becomes misinformation.

## Reduce documentation volume

The repo has too much documentation, spread across too many files. This causes:
staleness (version numbers drift), dilution (critical rules like pre_commit invariant
buried among lower-priority content), and cognitive overload (too much to read means
nothing gets read). Audit all doc/ files, schema principles.md and workflow.md files,
README.md, CLAUDE.md for redundancy and consolidation opportunities.

## Surface ai-title names alongside UUID prefixes

Session `.jsonl` files contain `ai-title` records with a human-readable session name.
The CHANGELOG and pre_commit output currently identify sessions only by 8-char UUID
prefix (e.g. `32bd7448…`). Surfacing the ai-title name alongside would make it much
easier to identify which session is which without cross-referencing the VS Code plugin.

### Survey results (2026-05-13)

**Within-session: 9 of 16 sessions have conflicting titles.** Claude Code re-titles
mid-session and sometimes changes the wording. Examples:

- `73f51bc1`: `'Fix staged changes commit issue'` vs `'Troubleshoot git commit failure'`
- `b0c38f0b`: `'Determine Claude model version in code session'` vs `'Determine Claude model version in session'`
- `e87e0735`: `'Review and analyze repository structure'` vs `'Thorough repository code review'`

**Cross-session: no duplicates** — each settled title is unique across sessions.

The within-session conflict means `ai-title` is not a stable per-session identifier as-is.
The VS Code UI also allows the user to rename a session manually, which writes another
`ai-title` record — indistinguishable from auto-generated ones. This means the last
`ai-title` record always reflects the user's final intent, making **last-wins** the
correct policy. This also gives the field a sane name: `currentSessionTitle` (the current,
user-visible title of the session).

### Schema implications

- `AiTitleRecord` — our name, can be renamed to `CurrentTitleRecord` (description-only
  change in schema terms, no validation effect).
- `aiTitle` — the actual field name written by Claude Code; cannot be renamed without
  breaking validation of real data. Update its description to reflect true semantics:
  the current user-visible session title, set by Claude Code (initially and on retitle)
  or by the user via the VS Code UI.
- `type: "ai-title"` — the discriminator value written by Claude Code; fixed.
- Considered a PATCH version bump (description-only, no validation change).
