# manifest schema changelog

The validation matrix (which local datum validates against which version) is machine-local
and git-ignored: each datum directory under `tmp/cache/` carries a `matrix.md` beside its
`validation/` logs, rendered at validation time (see `rsc/schema/WORKFLOW.md`).

---

## v1

Initial schema, minted from the flow change of 2026-08-24 (#522): requesting a
bulk export still emails a link, but the link now downloads this manifest -
version "1.0", four data_files, each a one-use export_url - where the
pre-manifest flow delivered one archive. Minted from the two manifests
observed on reading-room, 2026-08-24 (created 12:30:34Z and 12:31:52Z, one
account, two export requests): they differ only in created_at and the one-use
URLs. Closed throughout, category a closed enum over the observed four - so
the flow's next drift fails loudly by name, as this vintage itself would have
under a schema for its predecessor.
