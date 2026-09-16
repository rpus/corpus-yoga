# The readings behind `corpus-yoga indexing` and `corpus-yoga site`

Two commands produce and consume the intelligences' *readings* of the corpus —
the model's paid captures (`corpus-yoga indexing capture` → `data/output/indexing/inferred-*.json`) and
the user's curation (`corpus-yoga indexing` → `data/output/indexing/`). Corpus-derived, so
outside git: durable in `data/output/`, rebuildable in `tmp/cache/`. A user's curation is
inference exactly as a model's capture is; the repo privileges neither.

The format authorities are the schemas, not this file:

- `inferred-semantic-concepts.json` — `rsc/schema/indexing/semanticConcepts/` (latest
  version + CHANGELOG); the dashboard sizes its cloud by the weights, `indexing`
  borrows only the names as candidate headwords.
- `inferred-chat-categories.json` — `rsc/schema/indexing/chatCategories/`; id-keyed so
  identity survives renumbering; the palette is authored in `rsc/site/index.template.html`.
- `accepted-semantic-concepts.txt` / `rejected-semantic-concepts.txt` — headword and disposal formats in
  `corpus-yoga indexing --help`; every captured concept must reach one of them.

The disposal loop:

    corpus-yoga indexing capture → concepts   (model reads the corpus, paid)
    corpus-yoga indexing list-candidates            (candidates = inferred − accepted − rejected)
    accept <term> / reject <concept>    (your judgement, one per concept)
    corpus-yoga indexing sync                  (the book index over durable turn anchors)
