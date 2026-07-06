# README

This repo wrangles AI conversations, from Gemini (via browser capture only) and Claude (via browser capture, bulk export, and local coding sessions).

---

```bash
./PREREQUISITES.sh # read-only report: what this machine can run

# git clean -fdXn; git clean -fdxn

./RUNME.sh --capture-from-browser \
  --pay-for-inference # (requires `ANTHROPIC_API_KEY` in `env`)

./src/main/model/gen_model.sh

# ./src/test/pre_commit.sh
```

## Lay of the land

Everything is driven by shell entry points — there is no package or build system. Three git-ignored roots divide the data by lifecycle: **`ext/`** holds the raw inputs you supplied (one subdirectory per pipeline); **`gen/`** is the workshop — per-pipeline, datum-scoped derivations (validation logs, matrices, atomised pieces, presentations), always rebuildable, dying with their `ext/` datum; **`lib/`** is the library — what outlives any batch or run: the curated artifact library, the memory-snapshot timeline, the readable markdown corpus (`lib/markdown/`, what the server serves), and the viewer's static assets. (A fourth root, `logs/`, holds run-keyed diagnostics of the driving machinery — Safari capture runs, the serve daemon — timestamped and human-facing; the datum-keyed `.log` files inside `gen/` are different beasts: machine-read derived state, serving as validation memoisation and matrix input.) The root `RUNME.sh` orchestrates three pipelines, each with its own `PREP.sh` / `RUNME.sh` / `validate.sh` under `src/main/`:

| pipeline | input (`ext/…`) | what it does |
| --- | --- | --- |
| `browser-captures` | per-conversation captures via Safari (AppleScript + injected JS; Shortcut mode or scripted `capture_all()`): live API JSON for claude, DOM-scraped markdown for gemini (no API) | validates each claude capture against the `apiConversation` schema versions, then projects to markdown; gemini's scraped markdown is already the terminal artifact |
| `chat-exports` | official claude.ai bulk data exports (`data-*/` with `conversations.json` etc. — a synchronised snapshot of four components: conversations, memories, projects, users) | validates all four components, archives the non-conversation three verbatim into `gen/<batch>/` (bulk exports are the *only* log of chat memories), extracts embedded files/heredocs, optionally infers tables via the Anthropic API (`--pay-for-inference`), renders a dashboard, atomises the bulk array into per-conversation JSON, projects to markdown |
| `code-projects` | Claude Code CLI session `.jsonl` files (symlink to `~/.claude/projects`) | converts JSONL→JSON and validates against the `session` schema versions |

Downstream of capture, `src/main/model/project_markdown.py` renders clean markdown straight from the API JSON (no DOM scrape — `compare_markdown.py` is the safety net that verified parity with the legacy scrape), and `serve_markdown.sh` serves the results locally with LaTeX rendering.

Naming rule: within a batch, conversations are `<ordinal>-<slug>` (created-at order, one authority: `markdown_projection.ordered()`), but anything that *outlives* a batch — the curated artifact library `lib/artifacts/downloaded/` and the inferred tables — is keyed by conversation uuid (`<ordinal>-<slug>-<uuid8>` directories: the uuid8 suffix is the resolution key; the ordinal-slug prefix is presentation dressing, refreshed to current numbering whenever a pipeline run touches the dir — so listings sort in conversation order without the ordinal ever being trusted as identity; resolved via `src/main/chat-exports/library.py`), because ordinals renumber whenever the corpus changes. The LLM speaks ordinals, storage speaks uuid, presentation re-derives ordinals. The one deliberate exception proves the rule: memory snapshots (`lib/memories/`) are versions of a single mutable document, so there snapshot *time* is the identity — the dual keying. Note that `lib/` means "outlives the data that produced it", not "irreplaceable": `lib/markdown/` is rebuildable dressing (any pipeline run regenerates it), whereas `lib/artifacts/` and `lib/memories/` hold states nothing else records — treat those as precious.

The heart of the repo is the schema system under `rsc/schema/`: **versioned JSON Schemas** for each data shape (`apiConversation`, `conversations`, `session`, …). A schema whose validation behaviour must change is never edited in place — a new `vN+1.json` is minted and narrated in the schema's `CHANGELOG.md` (`### Restricted/Relaxed/Refactored since vN`); a machine-local `matrix.md` beside each datum's validation logs in `gen/` records which versions that datum validates against. Two gates keep schema and data honest: *coverage* (every datum validates against some version) and *frontier* (the newest datum validates against the latest version). `rsc/schema/model_join.csv` cross-references equivalent fields across pipelines so coupled changes aren't half-made. All of this is enforced by `src/test/pre_commit.py` plus paired diagnostic/repair scripts under `src/test/`. The end-to-end process for changing a schema is documented in `rsc/schema/WORKFLOW.md`.

## Prerequisites

Run `./PREREQUISITES.sh` for a read-only report of everything below against your machine (it changes nothing; `./RUNME.sh` is what creates directories and the venv).

- **Required**: `jq` and Python 3 (system bash 3.2 suffices). `RUNME.sh` creates a venv at `~/venvs/general` (override via `VENV=...`) and installs `src/requirements.txt` into it — note this venv is shared, not repo-local.
- **macOS-only, optional**: browser capture (`--capture-from-browser`) drives Safari via AppleScript, so it needs macOS with Safari logged in to claude.ai / gemini.google.com.
- **Optional**: `ANTHROPIC_API_KEY`, needed only for `--pay-for-inference` table inference.
- **Data**: the repo ships none — `ext/`, `gen/`, `lib/`, `logs/` are git-ignored. You supply your own bulk exports, captures, and Claude Code sessions (see "How to use").

On a fresh clone, `./RUNME.sh` is safe: it writes only to `ext/`, `gen/`, `lib/`, `logs/` and the venv, and pipelines with no input data report a skip rather than failing. `gen_model.sh` works from the committed schemas alone. `src/test/pre_commit.sh` groups its checks into three tiers: **code** (docs, cross-references) and **schema** (the committed schema artifacts) are deterministic on any clone and compared against the committed expected score; the **data** tier (per-datum matrices vs their validation logs, coverage, frontier) is machine-local — it runs only for pipelines with local data, is skipped with a notice otherwise, and its report never enters the committed `src/test/pre_commit.log` (which carries only the deterministic tiers, byte-identical on any clone); the full report prints to the terminal and lands in `logs/src/test/pre_commit.log`. A fresh clone should therefore pass, which makes the git hook installable anywhere: `ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit` (that exact symlink is load-bearing: the wrapper recognises hook context by its invoked name). As a hook, failures veto a commit only on the default branch (read from `origin/HEAD`); on any other branch — never on detached HEAD — the full report still prints but the commit proceeds: a branch commits work-in-progress, and its PR review is the gate. Run manually, `pre_commit.sh` always exits non-zero on failure. Either way the artifacts are staged by the run itself, so read a failure via `git diff --cached src/test/pre_commit.log`.

Contributing: PRs land by **squash only** — enforced as repository settings (merge commits and rebase-merge disabled; the PR title and body become the commit message; branches auto-delete on merge), so any `gh pr merge` or web merge behaves identically from any machine. The criterion behind the policy: *if a PR can't be squashed, it was not atomic* — main carries one narrated commit per landed idea, and the PR keeps the iteration. One local consequence of squashing: git cannot see a squashed branch as merged, so clean up with `git fetch --prune` and `git branch -D <branch>`.

## How to use

- Prepare new data
  - Open Safari, log in to <https://claude.ai>
  - Ask to "Export ('All') data" from <https://claude.ai/settings/data-privacy-controls>
  - Click on 24-hour emailed "Download Data" link (like <https://claude.ai/export/0fc4c1e0-4719-4e10-997a-697bf05599af/download/cdb658167a0d6dd4a2ffe829aeea9d15>)
  - Move downloaded folder/zip (like `data-*`) from `Downloads` into `ext/chat-exports` in this (cloned) repo (creating that directory first if needed), and unzip it if needed.
  - `export ANTHROPIC_API_KEY=<your-key>` (required for table inference by Claude)
- Capture markdown exports for each conversation via Safari (optional pre-processing step):
  - Open Safari, log in to <https://claude.ai> or <https://gemini.google.com>
  - **Shortcut trigger** — dispatches on whatever page the front tab shows (the invoker; the capture behaviour it selects is below):
    - Set up a macOS Shortcuts app shortcut: `caffeinate -dim osascript "$HOME/<path-to-repo-parent>/claude-export-yoga/src/main/browser-captures/export.applescript"`
    - With front tab on a specific conversation: captures that conversation *in place* (no navigation; the page is already loaded)
    - With front tab on <https://claude.ai/recents> or <https://gemini.google.com/app>: captures every listed conversation, each opened in its own transient tab and closed after — the listing tab is never navigated away
  - **Scripted trigger** — Python discovers every conversation and navigates through them in a dedicated work tab (the front tab is restored afterwards):
    - `./src/main/browser-captures/PREP.sh` (or `./RUNME.sh --capture-from-browser`)
  - **After having (or extending) a conversation, recapture it** — navigate to it and hit the Shortcut: an in-place recapture of just that conversation (seconds for the claude API fetch; a couple of minutes for a long scrape walk). The incremental loop:

    ```text
    src/run_python_script.sh src/main/browser-captures/audit_captures.py          # which captures are BAD (truncated / disagree with the api projection)
    src/run_python_script.sh src/main/browser-captures/audit_captures.py --live   # which conversations MOVED ON (drives Safari: claude updated_at sweep, gemini tail probes)
    Shortcut (or safari_capture.sh --id) on each flagged conversation             # selective in-place recapture
    ```

- Render clean markdown straight from the captured API JSON — no browser, no DOM scrape (preferred over the Safari markdown capture above; it only needs the `apiConversation` JSON each capture already fetches):
  - `src/run_python_script.sh src/main/model/project_markdown.py --browser-captures ext/browser-captures/claude --out lib/markdown/claude/conversations`
  - Projects each capture to the lean `markdownConversation` shape, validates it, and writes a flat directory of `<title>.md` with sane titles. Every turn heading carries an HTML anchor — the message uuid for claude (durable identity: `<file>.md#<uuid>` addresses a turn across renumberings), the role-count (`#human-3`) for gemini, whose scrapes have no uuids but are append-only. Comparisons are anchor-blind (the anchor rides the heading line, which `turn_seq` ignores).
  - Verify the projection reproduces (or improves on) the legacy DOM scrape — the safety net before retiring the scrape: `src/run_python_script.sh src/main/browser-captures/compare_markdown.py --api lib/markdown/claude/conversations --scrape ext/browser-captures/claude` (pure markdown-vs-markdown, paired by conversation id; add `--diff` for full per-conversation diffs). This runs automatically in the browser-captures pipeline (`RUNME.sh`) after the projection step.
  - For a bulk export, first split the one big `conversations.json` array into verbatim per-conversation pieces (validated against the `Conversation` definition — the only reader of the 24 MB array): `src/run_python_script.sh src/main/chat-exports/atomise_bulk.py --bulk-export ext/chat-exports/<batch>` → `gen/chat-exports/<batch>/json/`. Then render those pieces to markdown (same filenames): `src/run_python_script.sh src/main/model/project_markdown.py --bulk-export ext/chat-exports/<batch>` → `gen/chat-exports/<batch>/markdown/`.
  - Do later bulk exports supersede earlier ones? A batch is a synchronised snapshot of four components — conversations, memories, projects, users — and `src/run_python_script.sh src/main/chat-exports/compare_batches.py` puts each through the same unprejudiced unit/atom subset check (conversation → message uuids; project → doc uuids + prompt fingerprint; memory/user → content fingerprints). The latest snapshot is sufficient (exit 0) iff *every* component of every earlier batch is superseded — which components pass is an empirical finding, not an assumption (in practice conversations are append-only and supersede; the memory document is rewritten between exports and often doesn't — making the earlier batch the only record of that memory state). Runs automatically at the end of every chat-exports pipeline run, where it also compares the latest batch against the live captures per conversation (in-sync / capture-ahead / capture-stale-so-recapture / anomaly). Only delete a batch the verdict declares superseded — from both `ext/chat-exports/` and `gen/chat-exports/`; matrices are machine-local and die with it.
  - Cross-check the two sources agree (live API and bulk export should project to identical markdown per conversation): `src/run_python_script.sh src/main/model/compare_sources.py --browser-captures ext/browser-captures/claude --bulk-export ext/chat-exports/<batch>` (reads the batch's atomised `json/` pieces; add `--diff` for details).
- Browse and read captures as rendered markdown + LaTeX:
  - `src/main/model/serve_markdown.sh --markdown lib/markdown --daemon` then open <http://localhost:8182> — serves the whole corpus library: claude projections (`lib/markdown/claude/conversations/`), the chat-memory timeline (`lib/markdown/claude/memories/`), and gemini scrapes (`lib/markdown/gemini/conversations/`); turn deep links (`…/file/<path>.md#<anchor>`) jump to the turn once the page finishes rendering
  - The memory timeline is accumulated by the chat-exports pipeline (`accumulate_memories.py`): every distinct memory state deposits verbatim into the durable `lib/memories/<snapshot-time>.json` (content-deduplicated against the nearest earlier deposit — deposits are immutable and outlive their batches, which is what makes a memories-divergent batch safely deletable) and each deposit unwraps to `lib/markdown/claude/memories/<snapshot-time>.md` — a diffable record of what claude.ai believed at each export.
  - `src/main/model/serve_markdown.sh stop` to shut down

---

## Pre-public checklist

- [ ] Create a new repo (to get clean/sane git history).
- [ ] Add a LICENSE file.
- [ ] `src/main/schema_recommendations.py` — all 9 checks are stubbed; once implemented, call it from all pipeline `validate.sh` scripts on validation success
