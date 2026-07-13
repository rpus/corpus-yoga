# The readings behind `yoga indexing` and `yoga dashboard`

Two yoga commands produce and consume the intelligences' *readings* of the corpus —
the model's paid captures and the user's curation. That data is corpus-derived, so it
lives outside git with the rest of the corpus (**durable** in `output/`, **rebuildable**
in `cache/`); this committed file is its format contract. The command surface itself is
`rsc/cli/commands.csv`, and each script's `--help` is the authority on its interface.

## `yoga dashboard` — the model's captures (`output/dashboard/`)

Paid model readings behind the corpus dashboard (`rsc/site/index.html`, the shared
template), single-source and shared across rooms, refreshed deliberately and
out-of-band by `yoga dashboard capture` (both files; `--only <name>` for one),
reading the whole projected corpus (`output/markdown` — claude and gemini alike).
`yoga dashboard present` renders the CORPUS page free
(`src/main/chat-exports/present_corpus.py` → `cache/dashboard/presentation/`): keys
are the corpus ordinals over every source, claude lanes carry real spans (turn
anchors are UUIDv7s, whose first 48 bits are a timestamp), gemini lanes list
bar-less (its scrapes hold no time data), and the page-top source toggle filters
lanes and clouds alike. The per-batch pages (`src/main/chat-exports/present.sh` →
`cache/chat-exports/<batch>/presentation/`) remain export artifacts. Both captures
are `{columns, rows}` tables, schema'd like every other data class and validated
in-memory before promotion:

- **`semantic-concepts.json`** — schema `rsc/schema/dashboard/semanticConcepts/v2.json`
  (v1, untagged: `rsc/schema/dashboard/semanticConcepts/v1.json`; changelog:
  `rsc/schema/dashboard/semanticConcepts/CHANGELOG.md`):
  `{"columns": ["word", "count", "source"], "rows": [["mathematics", 100, "both"], …]}`.
  A weighted reading of the corpus's key concepts; the **count is salience** (top
  concept = 100), which the word cloud sizes by, and the **source names where the
  concept is salient** (`claude` / `gemini` / `both`), which the dashboard's
  source toggle filters by (a pre-v2 capture lacks the column; the toggle
  disables until the next capture). Two consumers, each taking what it needs:
  the dashboard uses the weights and tags (cloud sizing and filtering);
  `indexing` borrows only the names (candidate headwords, weights discarded).
- **`chat-categories.json`** — schema `rsc/schema/dashboard/chatCategories/v1.json`
  (changelog: `rsc/schema/dashboard/chatCategories/CHANGELOG.md`):
  `{"columns": ["id", "category"], "rows": [["<id>", "mathematics"], …]}`.
  Each conversation assigned exactly one category, **id-keyed** — claude uuid /
  gemini app id — so identity survives corpus renumbering; `present.sh` re-derives
  the current 1-based ordinal at render time. Every category must be an authored
  palette name — the `category → hue` map is a *design decision* authored inline in
  `rsc/site/index.html`, not a reading; category ∈ palette is a cross-file join
  constraint beyond the schema, which the capture checks separately before promoting.

## `yoga indexing` — the user's curation (`output/indexing/` + `cache/indexing/`)

The three **disposal states** of a captured concept: every concept in
`semantic-concepts.json` must reach `accepted` or `rejected`; whatever has reached
neither is a `candidate` (pending). Curation is inference by a user — the same act as
the model's capture, with a human oracle.

- **`accepted.txt`** (durable, `output/indexing/`) — adopted headwords:

      headword = alias, alias, …

  A plain line is a headword with no aliases; matching is case-insensitive on word
  boundaries; aliases locate under their headword. Append a bare word whenever one
  occurs to you — zero ceremony is the point. `# …` is a comment.

- **`rejected.txt`** (durable, `output/indexing/`) — declined concepts:

      term          # optional reason

  One rejected concept per line (the filename says *rejected*, so no verb prefix). A
  `# …`-only line is a comment.

- **`candidates.txt`** (rebuildable, `cache/indexing/`) — the pending queue, DERIVED:
  `semantic-concepts.json`'s names − `accepted` − `rejected`. Regenerate with
  `yoga indexing candidates`; never edit by hand (it is a `cache/` derivation, not a
  curated file).

## The loop

    yoga dashboard capture   ──▶ output/dashboard/semantic-concepts.json  (model reads the corpus)
                        │
    yoga indexing candidates ──▶ cache/indexing/candidates.txt  (pending = concepts − accepted − rejected)
                        │ (judgment)
       accepted.txt (accept)  ◀──── you ────▶  rejected.txt (reject)
                        │
       yoga indexing build ──▶ output/markdown/index.md  (locators to durable turn anchors)
