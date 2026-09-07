# generating schema.json from schema.ts

`2026-07-28/schema.ts` is upstream's source and `2026-07-28/schema.json` is generated from it. Upstream
does the generation with `scripts/generate-schemas.ts` (held here verbatim as
`2026-07-28/generate-schemas.ts`, pinned in `provenance.csv`), which for this lineage runs
one third-party tool and three text substitutions:

1. `typescript-json-schema` (npm, version 0.68.0 at the pinned commit, itself
   compiling with TypeScript 5.9.3) over `schema.ts`, selecting every exported
   type (`*`), with `--defaultNumberType integer --required --skipLibCheck`. This
   tool is what flattens every `extends` into inline properties, emits `const`,
   and orders definitions and keywords alphabetically. Its output is draft-07.
2. The `$schema` URL `http://json-schema.org/draft-07/schema#` is replaced by
   `https://json-schema.org/draft/2020-12/schema`.
3. `"definitions":` is replaced by `"$defs":` and `#/definitions/` by `#/$defs/`.

Nothing else touches the file: the 2020-12 label is a relabel of draft-07 output.

## reproducing it here

`corpus-yoga mcp reproduce` (`src/main/mcp/reproduce.sh`) runs upstream's own
generator over the committed `schema.ts`, in a container, at the pinned commit, and
diffs the result against the committed `schema.json`; its header states each
step, its effects and how to read the output. It commits nothing of
upstream beyond the two schema files: everything else the check needs is fetched at
the pin each run.

Demonstrated on home-room, 2026-09-07: the script printed no diff and
"reproduced", exit 0 - the regenerated file was byte-identical to the committed
`schema.json` (SHA256
`ef70b61f99b6d2e5e3b46863822eab08dff6a45bedc7a08914e0e5b133f40203`, the pinned
value); with one optional field added to a copy of `schema.ts`, it printed the
three generated lines as a diff and exited 1.
