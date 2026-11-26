# rsc/site - the rpus.co web surface, as authored

The hand-written inputs for <https://rpus.co>. The tree that serves is
`data/output/site/`, the one publish tree, where `data/output/site/<path>` is
`rpus.co/<path>`; nothing there is written by hand. `corpus-yoga site build` writes
all of it, and each file here says by its name what the build does with it (issues/650):

- **`<name>.html`** - a PAGE, complete as written. `corpus-yoga site build`
  copies it to `data/output/site/<name>.html`, byte for byte, and halts,
  naming the page, where a page's source has left. `rsc/site/corpus-yoga.html` is the corpus-yoga landing, served at
  <https://rpus.co/corpus-yoga.html>.
- **`index.template.html`** - a TEMPLATE, not a page: the corpus page with its
  data left out, six empty `<script type="application/json">` slots between
  `data-<table>.json:begin` and `:end` comments, and the category palette
  authored inline (a design decision, never filled). `corpus-yoga site build`
  (`present_corpus.py`) copies it, fills the slots from the corpus, the judged
  index and the categories, and writes `data/output/site/index.html`, its URL
  position.
  The per-batch pages (`present.sh`) fill the same template and stay in the
  workshop under `cache/pipeline/export/<batch>/presentation/`. A finished page
  fetches nothing at runtime: this repo only ever projects the corpus as it
  stands in `data/input/`.

Every `<name>.html` added here is published by the next `site build` and `site sync`. Pages are
self-contained by construction (no external fonts, scripts, or images),
light/dark via `prefers-color-scheme`, and honest about affordances: nothing
renders as a link unless it resolves.

## Deploying (Netlify via the private site repo)

The site deploys from a separate private GitHub repo that Netlify watches; its
root is the publish directory. `corpus-yoga site` says what a deploy would land, and
its `now:` names the command that lands it.

Netlify builds on push. The dry run states what changes in the corpus page in the
page's own terms, each data table compared by its identity column
(`src/main/compare_pages.py`, issues/652), since a line diff of two renders
misstates the change. The copy is a union: it lands new and changed files and
never deletes one, so a page that left rsc/site/ would stay on rpus.co unseen;
`corpus-yoga site build` halts on it, naming it, while it can still be seen. `ext/mnt/site` is the machine's hand-made symlink to the
private site repo's clone (the mount by reference `corpus-yoga status`
reports) - the repo's location itself is machine-local and not this repo's
business.
