# TODO

When something is discovered or changes: write it here. The human maintainer audits
TODO (and commits) and decides what gets promoted into permanent docs, acted on, or
discarded. Documentation updated in-place without going through TODO rots silently.

---

## Reduce documentation volume

The repo has too much documentation, spread across too many files. This causes:
staleness (version numbers drift), dilution (critical rules like pre_commit invariant
buried among lower-priority content), and cognitive overload (too much to read means
nothing gets read). Audit all doc/ files, schema principles.md and workflow.md files,
README.md, CONTRIBUTING.md for redundancy and consolidation opportunities.
