# mcp 2025-06-18 changelog

The 2025-06-18 lineage of the Model Context Protocol schema, held verbatim under `rsc/reference/mcp/2025-06-18/` at the upstream commit its `provenance.csv` rows pin (#587): one section per pin, newest first; the first section states the change from the lineage before it. A definition named here is the type of that name exported by `schema.ts` (`../generate.md` states the correspondence and the generation).

---

## 2ebb8060268e177b22598b403d6ba6764bb899ac

Taken 2026-09-09 (reading-room) by `corpus-yoga reference sync`'s procedure from upstream's `schema/2025-06-18/` at commit `2ebb8060268e177b22598b403d6ba6764bb899ac`, the newest commit touching that directory on upstream's main (upstream's fix of 2026-07-27 retyping `NumberSchema`'s bounds from integer to number in the generated JSON). 91 definitions under `definitions`, `$schema` `http://json-schema.org/draft-07/schema#`; schema.json 108,234 bytes, SHA256 `af845e7e5b9d27107d1690f0936022546177a1403e63ffb11470135b296a2e01`; schema.ts 42,430 bytes, SHA256 `7d7f4cc6f3adb76e3fd5e1eee6bab8b1e183cfaf719da66d2aa5661737ca9539`.

Against 2025-03-26: 11 definition names new, 3 absent - a name-level fact of upstream's files, not a house adjudication.

New: `BaseMetadata`, `BooleanSchema`, `ContentBlock`, `ElicitRequest`, `ElicitResult`, `EnumSchema`, `NumberSchema`, `PrimitiveSchemaDefinition`, `ResourceLink`, `ResourceTemplateReference`, `StringSchema`.

Absent: `JSONRPCBatchRequest`, `JSONRPCBatchResponse`, `ResourceReference`.

