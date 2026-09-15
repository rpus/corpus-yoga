# rsc/site - the rpus.co web surface, as authored

The hand-written inputs for <https://rpus.co>. The tree that serves is
`data/output/site/`, the one publish tree, where `data/output/site/<path>` is
`rpus.co/<path>`; nothing there is written by hand. Two verbs produce it, and
each file here says by its name which verb reads it (#650):

- **`<name>.html`** - a PAGE, complete as written. `corpus-yoga site sync`
  copies it to `data/output/site/<name>.html`, byte for byte, and prunes a page
  whose source has left. `rsc/site/corpus-yoga.html` is the corpus-yoga landing, served at
  <https://rpus.co/corpus-yoga.html>.
- **`index.template.html`** - a TEMPLATE, not a page: the corpus page with its
  data left out, six empty `<script type="application/json">` slots between
  `data-<table>.json:begin` and `:end` comments, and the category palette
  authored inline (a design decision, never filled). `corpus-yoga site render`
  (`present_corpus.py`, also the run's corpus-tail step) copies it, fills the
  slots from the corpus and writes `data/output/site/index.html`, its URL
  position - the one file in the publish tree that `site sync` never touches.
  The per-batch pages (`present.sh`) fill the same template and stay in the
  workshop under `tmp/cache/chat-exports/<batch>/presentation/`. A finished page
  fetches nothing at runtime: this repo only ever projects the corpus as it
  stands in `data/input/`.

Every `<name>.html` added here is published by the next `site sync`. Pages are
self-contained by construction (no external fonts, scripts, or images),
light/dark via `prefers-color-scheme`, and honest about affordances: nothing
renders as a link unless it resolves.

## Deploying (Netlify via the private site repo)

The site deploys from a separate private GitHub repo that Netlify watches; its
root is the publish directory. Deploying is one verb:

```bash
    corpus-yoga site publish          # dry: what would land, and the two acts
    corpus-yoga site publish --apply  # copy into ext/mnt/site, commit, push
```

Netlify builds on push. The copy lands new and changed files and mirrors no
deletion: a page or directory that left the publish tree is removed from the
site repo by hand. `ext/mnt/site` is the machine's hand-made symlink to the
private site repo's clone (the mount by reference `corpus-yoga prerequisites`
reports) - the repo's location itself is machine-local and not this repo's
business.
