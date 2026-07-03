# projects schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `gen/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v2

Now validates `019d1cb4-57a4-77a8-941c-9cf6078d4c31` in `data-0fc4c1e0-4719-4e10-997a-697bf05599af-1779222449-06d73759-batch-0000`.

### Refactored since v1

- Top-level schema changed from `type: array` (wrapping a single project object) to `type: object` — the data export places each project in its own file under `projects/`, not in a single array file. No change to the fields validated.

## v1

Initial schema. Validated against a single-element array containing a project object. The `projects/` directory format was not yet known.
