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

## v2

### Replaces

[v1.json](./v1.json)

#### Restricted

- `uuid (per user item)` gains the v4-UUID pattern (`^[0-9a-f]{8}-…$`, the literal of
  conversations' `UuidV4`) - the cell already carried the `UserUUID`
  cross-reference, and every corpus value matches (verified 2026-08-25 against
  data-0fc4c1e0-…-2026-08-24-12-30-34). States the constraint the values obey,
  restoring model_join row 145's identity claim truthfully after conversations
  narrowed its side to `UuidV4` (#527).

## v1

Initial schema.
