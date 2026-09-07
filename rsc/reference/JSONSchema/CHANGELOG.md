# JSONSchema reference changelog

This project holds the JSON Schema meta-schema as json-schema.org publishes it,
byte-for-byte, under `rsc/reference/` (#572): one lineage directory named as
upstream names it (`draft-04/`), holding `schema.json`. Draft-04 is the dialect
every house schema declares (`$schema: http://json-schema.org/draft-04/schema#`,
the meta-schema's own `id`), so the committed meta-schema is what
`check_schema_meta_validity` validates every house schema against. The latest
lineage is the reference and the rest history (#557); `provenance.csv` pins the
file's URL, etag and SHA256; `reference.json` names upstream. No lineage listing:
the drafts are not a dated series, and the house dialect is this one.

---

## draft-04

Taken 2026-09-07 (reading-room) from <https://json-schema.org/draft-04/schema>:
HTTP 200, `application/schema+json`, etag `7ce4bb1942375cf57495233f0ae4262f`,
4,357 bytes, SHA256
`e1489d0b4755f02793302591d3fcb8f07b6893a82a94f24895f8e4edf11b82e2`. Its
`properties` state every keyword's position (a schema, a map of schemas, a list
of schemas, a schema or a value, a value) - the declaration #571 derives the
schema walk from.
