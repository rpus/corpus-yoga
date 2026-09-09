# generating schema.json from schema.ts

In every lineage `schema.ts` is upstream's source and `schema.json` is generated from it; `corpus-yoga mcp reproduce` witnesses the newest lineage. Upstream
does the generation with `scripts/generate-schemas.ts` in its own repository at the
commit `provenance.csv` pins - fetched by the reproduction below each run, never
committed here - which for this lineage runs one third-party tool and three text
substitutions:

1. `typescript-json-schema` (npm, 0.68.0 at the pinned commit; it compiles with
   its own nested `typescript@5.9.3` - the top-level `typescript@6.0.3` that
   `package.json` names is not the one it uses) over `schema.ts`, selecting every exported
   type (`*`), with `--defaultNumberType integer --required --skipLibCheck`. This
   tool is what flattens every `extends` into inline properties, emits `const`,
   and orders definitions and keywords alphabetically. Its output is draft-07.
2. The `$schema` URL `http://json-schema.org/draft-07/schema#` is replaced by
   `https://json-schema.org/draft/2020-12/schema`.
3. `"definitions":` is replaced by `"$defs":` and `#/definitions/` by `#/$defs/`.

Nothing else touches the file: the 2020-12 label is a relabel of draft-07 output.

## names across the two files

Every `export interface` and `export type` in a lineage's `schema.ts` is a definition
of the same name in its `schema.json` (`definitions` up to 2025-06-18, `$defs` from
2025-11-25), and nothing else is: the `export const` values (`LATEST_PROTOCOL_VERSION`,
`JSONRPC_VERSION`, the error codes) are not emitted. Held for every lineage on
reading-room, 2026-09-09: 79 of 86 exports, 83 of 90, 91 of 98, 145 of 153, 155 of 165,
each time exactly the exports that are not constants. So a definition named in a
lineage changelog is the type of that name in `schema.ts`, and a name new or absent
between lineages is new or absent in both files. What the generator changes is shape,
not name: an interface's `extends` is flattened into inline properties (the composition
`corpus-yoga mcp sync` restores from `schema.ts` - #581), a type alias is inlined at
every use yet still emitted as its own definition, a literal type becomes `const`, an
optional member is a property absent from `required`, and the JSDoc comment becomes
`description` with its `@category` tag dropped.

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
