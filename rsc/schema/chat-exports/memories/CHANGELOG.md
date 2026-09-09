# memories schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

2026-09-09: the `UserUUID` cross-reference in v3's description fields was
amended in place: ../../model.json with the fragment `#/default/UserUUID` became
`../../../model/model.json` with the fragment `#/UserUUID` - the cross-family
model moved to `rsc/model/` and its table lost the `default` wrapper (#591). A
description change is not a validation change: no new version.

2026-07-13: the `UserUUID` cross-reference in v1's description fields was
amended in place: the fragment `#/UserUUID` became `#/default/UserUUID`
(against ../../model.json) — the old pointer had never navigated; xref
learned to follow `../` links and caught it. A description change is not a
validation change: no new version.

## v3

### Replaces

v2

#### Restricted (non-material)

- `account_uuid` gains the v4-UUID pattern (`^[0-9a-f]{8}-…$`, the literal of
  conversations' `UuidV4`) - the cell already carried the `UserUUID`
  cross-reference, and every corpus value matches (verified 2026-08-25 against
  data-0fc4c1e0-…-2026-08-24-12-30-34). States the constraint the values obey,
  restoring model_join row 145's identity claim truthfully after conversations
  narrowed its side to `UuidV4` (#527).

## v2

The restructure that reached projects in 2026-07 (its v2: each project in its
own file, the array wrapper gone) arrived for memories with the manifest-era
export of 2026-08-24 (#522): the export ships one object per account as a
per-account file under a memories directory, where the pre-manifest export
wrapped the same object in a single-element array at the batch root. The
deposit hoists the file to memories.json beside the other components (the
maintainer's ruling, 2026-08-24), so the component's name and place are
unchanged and only the shape moved. Fields unchanged.

### Replaces

v1

#### Relaxed

- The bare per-account object is admitted - the manifest-era shape, validated
  against the 2026-08-24 export's file at mint.

- Refuses thereby: the array wrapper - the pre-manifest memories.json (observed
  resting in the one held batch-0000 export) passes v1 and fails v2 - each
  era's shape rejected by the other's version, as the eras rule.

#### Refactored

None.

## v1

Initial schema.
