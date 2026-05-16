# model

Two independent tools: a cross-pipeline schema model generator and a local markdown viewer for browser captures.

---

## Schema model generation

Generates per-schema definition catalogues as candidates for the hand-curated `rsc/schema/model.json`.

```bash
src/main/model/gen_model.sh
```

For each versioned schema across all pipelines, traverses its definitions and records each one's description and every path at which it is referenced. Output goes to `gen/model/{schema}/v{N}.json`. `rsc/schema/model.json` is then hand-curated from these candidates.

---

## Browser-capture viewer

`ext/browser-captures/` contains markdown transcripts of Claude conversations captured via Safari. This tool starts a local HTTP server so you can read those transcripts in your web browser, rendered as markdown with LaTeX math.

**Why use it:** the raw markdown files are readable but contain LaTeX that renders badly as plain text. This renders them properly, and adds a searchable index of all captures sorted newest first.

```bash
src/main/model/serve_markdown.sh --browser-captures ext/browser-captures --daemon
src/main/model/serve_markdown.sh stop
src/main/model/serve_markdown.sh --browser-captures ext/browser-captures   # foreground
```

Then open `http://localhost:8182` in your web browser. You will see a list of all `.md` files in `ext/browser-captures/` sorted newest first, with a search box. Clicking a file renders it as markdown with LaTeX math.

On first run, downloads rendering assets (marked.js, KaTeX) to `lib/search-static/`.

---

## Files

| File | What it does |
| --- | --- |
| `gen_model.sh` / `gen_model.py` | Runs `gen_model_candidate.py` for every versioned schema; writes `gen/model/` |
| `gen_model_candidate.py` | Generates a definition catalogue for one schema: descriptions + reference paths |
| `serve_markdown.sh` / `serve_markdown.py` | Local HTTP server: index, full-text search, and markdown+LaTeX rendering of captures |
