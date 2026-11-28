# The readings behind `corpus-yoga indexing` and `corpus-yoga site`

Two commands produce and consume the intelligences' *readings* of the corpus —
the model's paid captures (`corpus-yoga indexing capture` → `data/output/indexing/capture/<stamp>/`) and
the reader's choice among them (`corpus-yoga indexing adopt` → the capture in use,
`data/output/indexing/inferred-*.json`). Corpus-derived, so outside git: durable in `data/output/`,
rebuildable in `cache/`.

The format authorities are the schemas, not this file:

- `inferred-semantic-concepts.json` — `rsc/schema/indexing/semanticConcepts/` (latest
  version + CHANGELOG); `indexing build` takes the names as headwords where a turn phrases them, and
  a batch page sizes its cloud by the weights.
- `inferred-chat-categories.json` — `rsc/schema/indexing/chatCategories/`; id-keyed so
  identity survives renumbering; the palette is authored in `rsc/site/index.template.html`.
The order:

    corpus-yoga indexing capture               (model reads the conversation titles, paid; deposited, and
                                               names which concepts the corpus can index, issues/644)
    corpus-yoga indexing adopt <stamp>         (the deposit becomes the capture in use)
    corpus-yoga indexing build                  (the index, indexed-semantic-concepts.json: each concept of the
                                               capture in use a turn phrases, with the turns it is found in)
    corpus-yoga server build / site build       (the book index the server serves / the corpus page,
                                               both written from the index)
