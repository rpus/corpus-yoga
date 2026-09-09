# JSONSchema reference

This project holds the JSON Schema meta-schema as json-schema.org publishes it,
byte-for-byte, under `rsc/reference/JSONSchema/` (#572): one directory per draft,
named as upstream names it (`draft-04/`), holding `schema.json` and its own
`CHANGELOG.md` (one section per pin - #587). Draft-04 is the dialect every house
schema declares (`$schema: http://json-schema.org/draft-04/schema#`, the
meta-schema's own `id`), so the committed meta-schema is what
`check_schema_meta_validity` validates every house schema against, and the
declaration `src/schema_walk.py` derives every keyword's position from (#571).
`provenance.csv` pins the file's URL, etag and SHA256; `reference.json` names
upstream. No lineage listing: the drafts are not a dated series, so
`corpus-yoga reference` probes the pinned rows only, and `corpus-yoga reference sync`
refetches a row whose bytes at its URL no longer hash as pinned.
