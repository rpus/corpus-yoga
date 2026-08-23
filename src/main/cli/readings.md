# The readings behind `corpus-yoga indexing` and `corpus-yoga site`

Two commands produce and consume the intelligences' *readings* of the corpus —
the model's paid captures (`corpus-yoga indexing capture` → `data/output/dashboard/`) and
the user's curation (`corpus-yoga indexing` → `data/output/indexing/`). Corpus-derived, so
outside git: durable in `data/output/`, rebuildable in `tmp/cache/`. A user's curation is
inference exactly as a model's capture is; the repo privileges neither.

The format authorities are the schemas, not this file:

- `semantic-concepts.json` — `rsc/schema/dashboard/semanticConcepts/` (latest
  version + CHANGELOG); the dashboard sizes its cloud by the weights, `indexing`
  borrows only the names as candidate headwords.
- `chat-categories.json` — `rsc/schema/dashboard/chatCategories/`; id-keyed so
  identity survives renumbering; the palette is authored in `rsc/site/index.html`.
- `accepted.txt` / `rejected.txt` — headword and disposal formats in
  `corpus-yoga indexing --help`; every captured concept must reach one of them.

The disposal loop:

    corpus-yoga indexing capture → concepts   (model reads the corpus, paid)
    corpus-yoga indexing list-candidates            (pending = concepts − accepted − rejected)
    accept <term> / reject <concept>    (your judgement, one per concept)
    corpus-yoga indexing sync                  (the book index over durable turn anchors)
