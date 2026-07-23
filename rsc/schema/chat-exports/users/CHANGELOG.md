# users schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

2026-07-13: the `UserUUID` cross-reference in v1's description fields was
amended in place: the fragment `#/UserUUID` became `#/default/UserUUID`
(against `../../model.json`) — the old pointer had never navigated; xref
learned to follow `../` links and caught it. A description change is not a
validation change: no new version.

## v1

Initial schema.
