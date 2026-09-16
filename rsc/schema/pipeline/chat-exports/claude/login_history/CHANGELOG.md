# login_history schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

2026-09-09: the `UserUUID` cross-reference in v1's description fields was
amended in place: ../../model.json with the fragment `#/default/UserUUID` became
`../../../../../model/model.json` with the fragment `#/UserUUID` - the cross-family
model moved to `rsc/model/` and its table lost the `default` wrapper (#591). A
description change is not a validation change: no new version.

## v1

Initial schema, minted 2026-08-24 with the manifest-era intake (#522): the
component had shipped in every observed export but never had a family. One
shape across both vintages - an object of `login_events`, each event the
account uuid, instant, IP, parsed user agent, method, and coarse location;
`os_version`, `region` and `city` observed null; `method` observed only as
"google", the set left open. Validated against both held exports' files
(29 and 30 events) at mint.

#### Refactored

- The description that points at the cross-family model (v1, in place) is the
  relative path from the family's address since 2026-09-16 (#632),
  `rsc/schema/pipeline/chat-exports/claude/login_history/`: `../../../../../model/model.json#/UserUUID`.
  No validation effect.
