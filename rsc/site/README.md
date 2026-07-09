# rsc/site — the rpus.co web surface, as committed data

The authored HTML for <https://rpus.co>, in one committed home rather than loose
in `rsc/`. The directory mirrors the site's path space, so a file here serves at
the matching URL:

- **`index.html`** → `rpus.co/` — the homepage: the corpus dashboard. A TEMPLATE,
  not a finished page: `present.sh` copies it to each batch's
  `gen/.../presentation/index.html` and fills it (inferred category hues, tables);
  the filled result is what deploys.
- **`yoga/index.html`** → `rpus.co/yoga/` — the yoga landing, a static, already
  complete page.

Self-contained by construction (no external fonts, scripts, or images), light/dark
via `prefers-color-scheme`, and honest about affordances: nothing renders as a
link unless it resolves.

## Deploying (Netlify via the private site repo)

The site deploys from a separate private GitHub repo that Netlify watches;
its root is the publish directory (the same repo the post-inference dashboard
`index.html` is copied into). Deploying a page from here is a copy plus a
push in that repo:

    cp -R rsc/site/yoga <path-to-site-repo>/
    cd <path-to-site-repo> && git add yoga && git commit -m "yoga landing" && git push

Netlify builds on push; `rpus.co/yoga/` serves the directory index. The site
repo's location is machine-local (it is not this repo's business) — a
hand-made `ext/site` symlink to its clone is the conventional binding if a
`yoga`-verb deploy step is ever wanted.
