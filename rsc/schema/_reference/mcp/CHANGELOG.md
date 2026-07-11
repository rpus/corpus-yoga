# mcp reference-snapshot changelog

This family is a VERBATIM UPSTREAM SNAPSHOT, not a house schema: the Model
Context Protocol spec, converted to draft-04 so `model_join.csv`'s `mcp_path`
column can point into it. No data is validated against it (it enters no
pipeline, no coverage or frontier gate), and the house style diagnostics
deliberately skip `_reference/` families — repairing upstream text to satisfy
house rules would falsify the snapshot. Each version's `description` field
carries its own provenance: the upstream raw URL, the commit it was taken
from, and the upstream file's SHA256, which `check_mcp_schema` compares
against the live URL. When upstream drifts, mint the next version beside this
one — the old snapshot is history, kept (versioning replaced the old
update-in-place remedy, which destroyed it).

---

## v1

The MCP schema of 2025-11-25, taken at upstream commit `357adac` and converted
to draft-04. Lived as a single flat file beside this family (no versions, no
changelog, updated in place) until 2026-07-10, when the reference joined the
versioned-family system (same grammar as every other `model_join` column:
`_reference/mcp#/definitions/…`, resolved against the latest version).
