# rsc/site — the rpus.co web surface, as authored sources

The authored inputs for <https://rpus.co>. The tree that actually serves is
`data/output/site/` — the ONE publish tree, where `data/output/site/<path>` is
`rpus.co/<path>` — assembled by `corpus-yoga site sync` from the page directories here.
This directory's root FILES are inputs, not pages, and stay behind:

- **`index.html`** — a TEMPLATE, not a finished page: both presenters copy it and
  inject the data tables (the category palette is authored inline here — design,
  never filled). The corpus-wide render is `present_corpus.py`'s (`corpus-yoga dashboard
  sync`), which writes the finished page to `data/output/site/index.html` — its URL
  position, and the one file in the publish tree that `site sync` never touches.
  The per-batch pages (`present.sh`) are export-scoped and stay in the workshop
  under `tmp/cache/chat-exports/<batch>/presentation/`. The tables the page is
  built from are self-contained inside it (inlined `<script>` blocks); it fetches
  nothing at runtime — this repo only ever projects the corpus as it stands in
  `data/input/`.
- **`corpus-yoga/`** — a page directory: everything in it is published verbatim at
  `rpus.co/corpus-yoga/`. `rsc/site/corpus-yoga/index.html` is the corpus-yoga landing, static and
  complete. `rsc/site/corpus-yoga/dataflow.dot` is the repo's dataflow map: tiers as
  clusters, one edge per
  writing command — black the feed-forward kernel, red dashed the reflexive
  layer, blue the sends, green the human's own writes. The `.dot` is the one
  committed source — hand-curated until the resource registry can derive it.
  `site sync` renders `dataflow.svg` + `dataflow.png` beside the copied page in
  the publish tree (derived presentation, L5: never committed, landed in the
  output tier); without graphviz the renders are skipped and the status says so.

Every page directory added here is published whole by the next `site sync`.
Pages are self-contained by construction (no external fonts, scripts, or
images), light/dark via `prefers-color-scheme`, and honest about affordances:
nothing renders as a link unless it resolves.

## Deploying (Netlify via the private site repo)

The site deploys from a separate private GitHub repo that Netlify watches; its
root is the publish directory. Deploying is one verb:

```bash
    corpus-yoga site publish          # dry: what would land, and the two acts
    corpus-yoga site publish --apply  # copy into ext/mnt/site, commit, push
```

Netlify builds on push; `rpus.co/corpus-yoga/` serves the directory index.
`ext/mnt/site` is the machine's hand-made symlink to the private site repo's
clone (the mount by reference `corpus-yoga prerequisites` reports) — the repo's
location itself is machine-local and not this repo's business.
