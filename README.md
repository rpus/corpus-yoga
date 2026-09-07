# corpus-yoga

Wrangles AI conversations — Claude (bulk export, browser capture, Claude Code
sessions) and Gemini (browser capture) — into one validated, readable, indexed
corpus.

## Quickstart

```bash
./src/main/cli/prerequisites/prerequisites.sh sync --apply   # pre-venv, once: mint the venv (bare, the same report read-only)
./corpus-yoga prerequisites          # read-only: what this machine can run
./corpus-yoga browser capture        # acquire: Safari sweep into data/input/
./corpus-yoga pipeline run           # the usr gate: validate, extract, project (--plan previews)
./corpus-yoga server start --daemon  # read the corpus at http://localhost:8182
./corpus-yoga indexing capture       # PAID: the model re-reads the corpus for the index tables
./corpus-yoga site render            # render the corpus page from corpus + captures
./corpus-yoga test run               # the dev gate: the hermetic suite over src/ and rsc/
```

`./corpus-yoga -h` lists every command with its summary; `./corpus-yoga commands [<command>]`
prints man entries; `./corpus-yoga <command> <verb> --help` asks each target itself.

## The tiers

| root | lifecycle | medium | loss cost |
| --- | --- | --- | --- |
| `.` + `rsc/` + `src/` | machinery | git | none — clone again |
| `data/input/` | input | iCloud | none — as long as iCloud holds it |
| `tmp/cache/` | cache | local | none — `corpus-yoga cache sync` rebuilds it from the registry (`rsc/cache_io.csv`) |
| `tmp/logs/` | run history | local | disposable |
| `data/output/` | historical accumulation | iCloud | the one irreplaceable tier — deposits, curation, readings |

Inputs are typed `data/input/<provider>/<channel>/<capture>/` — providers `claude`,
`gemini` have channels `chat`, `code` and captures `bulk-export`, `browser-API`,
`browser-DOM`, `machine-transport`; `github` has `forge` and `gh-CLI`. The readable corpus is
`data/output/markdown/<provider>/<channel>/`, and the pipelines never read
`~/.claude/projects` — sessions arrive via `corpus-yoga agent capture` through the
prefix-gated store.

Git carries machinery only. The corpus - conversation text, the downloaded
artifact libraries, titles, readings - has one home, `data/`; `data/`, `tmp/`,
`ext/` and `machine-name.txt` are ignored and track nothing, so neither a corpus
datum nor a machine fact (a username, a home path) is representable in a commit,
and `corpus-yoga test run` holds both facts over every tracked file (L2). The history is
kept as it stands: its early commits carry the maintainer's own conversation
artifacts (removed from the tree on 2026-05-16) and one dashboard of the
maintainer's conversation titles, and nothing of any third party - audited on
reading-room, 2026-08-22, at 17e173c (#498).

## Where facts live

- the command surface: `src/main/cli/` (one file per command, one per subcommand) — grammar and gates: `src/main/cli/README.md`
- the doctrine (operations, laws L1–L10): `rsc/CALCULUS.md` (`corpus-yoga calculus`)
- every data shape: `rsc/schema/<root>/<family>/vN.json` - the roots are the three pipelines, `dashboard` (the shapes of the paid dashboard readings) and `protocol` (house schemas derived from upstream references) - history in its `CHANGELOG.md`, minting in `rsc/schema/WORKFLOW.md`
- every upstream reference artefact: `rsc/reference/<project>/<lineage>/…`, byte-for-byte (the MCP `schema.json` and `schema.ts`, the JSON Schema draft-04 meta-schema), pinned by the `provenance.csv` beside it
- naming vintages (as data): `rsc/naming/library_dir_vintages.csv`, `rsc/naming/memory_deposit_vintages.csv`
- the machine registry: `rsc/machine/machines.csv`; this machine's binding to it: the gitignored `machine-name.txt` at the root (`corpus-yoga prerequisites` reports both)
- commit trailers (the `Signature:` grammar): `rsc/test/prepare-commit-msg-hook.sh` (the hook that stamps it)
- the forge's merge settings (server-side, so declared here as data): `src/main/cli/forge/forge.csv` (`corpus-yoga prerequisites` reconciles them against the live forge and prints each drift's own `gh` remedy)
- the checks: `src/test/dev/run.py` (`corpus-yoga test run`); cross-references: `corpus-yoga test xref` (bare `corpus-yoga test` shows status)

## Getting data

Bulk export: claude.ai → Settings → Data privacy controls → "Export data"; unzip
the emailed `data-*` into `data/input/claude/chat/bulk-export/`. Browser captures:
Safari logged in to claude.ai / gemini.google.com, then `corpus-yoga browser capture`
(or the macOS Shortcut: `open -a Terminal src/main/cli/browser/capture.command`
— Terminal holds the folder permissions; Shortcuts' own shell is silently denied).
Code sessions: `corpus-yoga agent capture --all`. The forge's ledger (issues, pull
requests, comments, reviews, labels, blocked_by edges): `corpus-yoga forge capture` -
one stamped deposit under `data/input/github/forge/gh-CLI/` per run. Paid model readings:
`corpus-yoga indexing capture` (needs `ANTHROPIC_API_KEY` set; `corpus-yoga prerequisites`
reports it), rendered free by `corpus-yoga site render`. Batch disposal is computed, never assumed: `corpus-yoga supersede check`.

## Prerequisites

`jq` and Python 3; `./src/main/cli/prerequisites/prerequisites.sh sync --apply` creates the
shared venv (`~/venvs/general`, override via `VENV=`) and installs `src/requirements.txt` -
the one place the name `python3` survives (#478): `corpus-yoga` itself and every `.py` run in the venv. Browser capture needs macOS + Safari. The repo ships no
data — `data/input/ tmp/cache/ data/output/ tmp/logs/` are git-ignored. Install the hook (required;
`corpus-yoga prerequisites` reports whether it is):
`./corpus-yoga test install-hook`. And the
signature hook (convention, optional; grammar in its own header):
the same `./corpus-yoga test install-hook` — it installs both.

## Changing it

Two audiences beyond the one this file addresses, and each has its own home. A
**developer** changes code and runs the **dev gate** — `corpus-yoga test run` over
`src/test/dev/`, hermetic (no network, no `gh`, no corpus), which is why the pre-commit
hook can depend on it. The developer is typically an agent, building in a detached
worktree that holds no corpus and needs none: a commit is src/ and rsc/ only, the
dev gate is complete over exactly that, so the private corpus is never in the
agent's need or extent - need-to-know by construction, not by policy. An **owner**
merges, prunes, and keeps the forge's declared
settings: `./CONTRIBUTING.md`. The reader of this file holds the other gate already:
`corpus-yoga pipeline run` is the **usr gate** — it arbitrates that the verbs run over a
corpus, which the dev gate, blind to data by design, cannot; every act that touches
the corpus runs in the owner's room, under the owner's hands.

## The public surface

Pages for <https://rpus.co> live under `rsc/site/`; deploy per `rsc/site/README.md`.
