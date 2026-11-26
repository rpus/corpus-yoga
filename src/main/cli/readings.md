# The readings behind `corpus-yoga indexing` and `corpus-yoga site`

Two commands produce and consume the intelligences' *readings* of the corpus —
the model's paid captures (`corpus-yoga indexing capture` → `data/output/indexing/inferred-*.json`) and
the user's curation (`corpus-yoga indexing` → `data/output/indexing/`). Corpus-derived, so
outside git: durable in `data/output/`, rebuildable in `cache/`. A user's curation is
inference exactly as a model's capture is; the repo privileges neither.

The format authorities are the schemas, not this file:

- `inferred-semantic-concepts.json` — `rsc/schema/indexing/semanticConcepts/` (latest
  version + CHANGELOG); `indexing` borrows only the names as candidate headwords, and
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
                                               both written from the judged index)
