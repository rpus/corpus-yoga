# mcp reference

This project holds the Model Context Protocol schema as upstream publishes it,
byte-for-byte, under `rsc/reference/mcp/` (#572): one directory per dated lineage
upstream lists, named as upstream names it, each holding `schema.json` and
`schema.ts` and its own `CHANGELOG.md` (one section per pin, the first stating the
change from the lineage before - #587). `provenance.csv` pins every file's URL,
upstream commit and SHA256; `reference.json` names upstream, the lineage listing
(the dated `schema/` directory) and the files held per lineage. `corpus-yoga reference`
reports what upstream lists against what is held and whether the held bytes still
hash as pinned; `corpus-yoga reference sync` fetches what is missing or drifted and
writes the provenance rows - the changelog section is the hand act. The dev gate
holds every file verbatim to its pin, every lineage directory declared, and every
pin's changelog section present (`check_reference`); currency against upstream is
the verb's report, never the gate's.

The latest lineage is what the house reads: `corpus-yoga mcp sync` extracts its
`schema.ts`'s extends clauses and type aliases (#581) and derives
`rsc/schema/protocol/mcpMessage` from it, and `corpus-yoga mcp reproduce` witnesses
that upstream's generator turns its `schema.ts` into its `schema.json`
(`generate.md` states the generation). No data is validated against any lineage
and no house diagnostic runs over one.
