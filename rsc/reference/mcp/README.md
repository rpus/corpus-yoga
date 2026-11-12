# mcp reference

This project holds the Model Context Protocol schema as upstream publishes it,
byte-for-byte, under `rsc/reference/mcp/` (issues/572): one directory per dated lineage
upstream lists, named as upstream names it, each holding `schema.json` and
`schema.ts` and its own `CHANGELOG.md` (one section per pin, the first stating the
change from the lineage before - issues/587). `provenance.csv` pins every file's URL,
upstream commit and SHA256; `reference.json` names upstream, the lineage listing
(the dated `schema/` directory) and the files held per lineage. `corpus-yoga reference
fetch` records what upstream publishes under `tmp/reference/fetch/mcp/`, each
lineage's files with `fetched.csv` beside them in `provenance.csv`'s columns, and
writes nothing here; `corpus-yoga reference` reads that record and says each file
missing here or drifted from its pin, and `corpus-yoga mcp` judges upstream's
`schema.json` as fetched against the committed version. What a fetch brings reaches
this directory as a commit, never by a verb: the fetched files and their
`fetched.csv` rows copied in, the changelog section written by hand, and the
family re-derived (`src/main/mcp/derivation.json` names the lineage). The dev gate
holds every file verbatim to its pin, every lineage directory declared, and every
pin's changelog section present (`check_reference`); currency against upstream is
the fetch's record, never the gate's.

The latest lineage is what the house reads: `corpus-yoga mcp derive` extracts its
`schema.ts`'s extends clauses and type aliases (issues/581) and derives
`rsc/schema/mcp/2026-07-28/mcpMessage` from it, and `corpus-yoga mcp reproduce` witnesses
that upstream's generator turns its `schema.ts` into its `schema.json` - the newest
lineage only; the earlier lineages' files are held at their pins unwitnessed
(`generate.md` states the generation and how the two files' names correspond). No data is validated against any lineage
and no house diagnostic runs over one.
