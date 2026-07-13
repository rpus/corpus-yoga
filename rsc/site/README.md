# rsc/site — the rpus.co web surface, as committed data

The authored HTML for <https://rpus.co>, in one committed home rather than loose
in `rsc/`. The directory mirrors the site's path space, so a file here serves at
the matching URL:

- **`index.html`** → `rpus.co/` — the homepage: the corpus dashboard. A TEMPLATE,
  not a finished page — both presenters copy it and inject the data tables (the
  category palette is authored inline here — design, never filled). The corpus-wide
  page is what deploys: `present_corpus.py` (`yoga dashboard present`) writes it to
  `output/dashboard/presentation/index.html`, a library artifact beside the
  `output/dashboard/` captures it summarises. The per-batch pages (`present.sh`) are
  export-scoped and stay in the workshop under `cache/chat-exports/<batch>/presentation/`.
  The tables the page is built from are self-contained inside it (inlined `<script>`
  blocks); it fetches nothing at runtime — this repo only ever projects the corpus as
  it stands in `input/`.
- **`yoga/index.html`** → `rpus.co/yoga/` — the yoga landing, a static, already
  complete page.

Self-contained by construction (no external fonts, scripts, or images), light/dark
via `prefers-color-scheme`, and honest about affordances: nothing renders as a
link unless it resolves.

## Deploying (Netlify via the private site repo)

The site deploys from a separate private GitHub repo that Netlify watches;
its root is the publish directory (the same repo the presented dashboard
`index.html` is copied into). Deploying a page from here is a copy plus a
push in that repo:

    cp -R rsc/site/yoga <path-to-site-repo>/
    cd <path-to-site-repo> && git add yoga && git commit -m "yoga landing" && git push

Netlify builds on push; `rpus.co/yoga/` serves the directory index. The site
repo's location is machine-local (it is not this repo's business) — a
hand-made `input/site` symlink to its clone is the conventional binding if a
`yoga`-verb deploy step is ever wanted.
