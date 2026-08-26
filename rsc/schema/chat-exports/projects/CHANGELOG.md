# projects schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

2026-07-13: the `UserUUID` cross-reference in v1 and v2's description fields was
amended in place: the fragment `#/UserUUID` became `#/default/UserUUID`
(against `../../model.json`) — the old pointer had never navigated; xref
learned to follow `../` links and caught it. A description change is not a
validation change: no new version.

## v3

### Replaces

v2

#### Restricted

- `creator.uuid` gains the v4-UUID pattern (`^[0-9a-f]{8}-…$`, the literal of
  conversations' `UuidV4`) - the cell already carried the `UserUUID`
  cross-reference, and every corpus value matches (verified 2026-08-25 against
  data-0fc4c1e0-…-2026-08-24-12-30-34). States the constraint the values obey,
  restoring model_join row 145's identity claim truthfully after conversations
  narrowed its side to `UuidV4` (#527).

## v2

Now validates `019d1cb4-57a4-77a8-941c-9cf6078d4c31` in `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1779222449-06d73759-batch-0000`.

### Replaces

v1

#### Refactored

- Top-level schema changed from `type: array` (wrapping a single project object) to `type: object` — the data export places each project in its own file under `projects/`, not in a single array file. No change to the fields validated.

## v1

Initial schema. Validated against a single-element array containing a project object. The `projects/` directory format was not yet known.
