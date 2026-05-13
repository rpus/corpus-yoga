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
