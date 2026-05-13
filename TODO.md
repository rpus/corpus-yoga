# TODO

## pre-commit hook leaves xref.csv and pre_commit.log dirty after commit

The pre-commit hook runs `pre_commit.sh`, which regenerates `xref.csv` and
`pre_commit.log` — but does not stage them. After every commit they are left dirty in
the working tree. The hook should either auto-stage these generated files before the
commit proceeds, or the workflow should require them to be staged manually before
committing.

## gen_changelog_matrix --write can silently encode failures as expected

The fix hint emitted by pre_commit (`gen_changelog_matrix --write`) writes whatever
the current validation logs say — including failures. If run before understanding why
a session is failing, it registers the failure as expected and masks it from future
pre_commit runs. The hint should either warn when it is about to encode a ✗, or the
workflow doc should make this risk explicit.

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

## Use git diff on pre_commit.log, not tail/grep on live output

pre_commit.log is committed so that `git diff src/test/pre_commit.log` shows exactly
what changed — pass→fail, fail→pass, new checks, removed checks — without
filtering. Running tail or grep on live pre_commit.sh output is error-prone and
unnecessary. The workflow should always be: run pre_commit.sh, then read the diff.
