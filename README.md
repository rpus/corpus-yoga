# claude-export-yoga

Wrangles AI conversations — Claude (bulk export, browser capture, Claude Code
sessions) and Gemini (browser capture) — into one validated, readable, indexed
corpus.

## Quickstart

```bash
./yoga prerequisites          # read-only: what this machine can run
./yoga browser capture        # acquire: Safari sweep into data/input/
./yoga pipeline run           # process: validate, extract, project (--plan previews)
./yoga server start --daemon  # read the corpus at http://localhost:8182
./yoga test run               # the three-tier gate suite
```

`./yoga -h` lists every command with its summary; `./yoga commands [<command>]`
prints man entries; `./yoga <command> <verb> --help` asks each target itself.

## The tiers

| root | lifecycle | medium | loss cost |
| --- | --- | --- | --- |
| `.` + `rsc/` + `src/` | machinery | git | none — clone again |
| `data/input/` | input | iCloud | none — the medium carries it (sessions: once stashed via `yoga agent capture --all`) |
| `tmp/cache/` | cache | local | none — `yoga cache sync` rebuilds it from the registry (`rsc/cache_io.csv`) |
| `tmp/logs/` | run history | local | disposable |
| `data/output/` | historical accumulation | iCloud | the one irreplaceable tier — deposits, curation, readings |

Inputs are typed `data/input/<provider>/<channel>/<capture>/` — providers `claude`,
`gemini`; channels `chat`, `code`; captures `bulk-export`, `browser-API`,
`browser-DOM`, `machine-transport`. The readable corpus is
`data/output/markdown/<provider>/<channel>/`, and the pipelines never read
`~/.claude/projects` — sessions arrive via `yoga agent capture` through the
prefix-gated store.

## Where facts live

- the command surface: `src/main/cli/` (one file per command, one per subcommand) — grammar and gates: `src/main/cli/README.md`
- the doctrine (operations, laws L1–L8): `rsc/CALCULUS.md` (`yoga calculus`)
- every data shape: `rsc/schema/<pipeline>/<family>/vN.json`, history in its `CHANGELOG.md`, minting in `rsc/schema/WORKFLOW.md`
- naming vintages (as data): `rsc/naming/library_dir_vintages.csv`, `rsc/naming/memory_deposit_vintages.csv`
- the machine registry: `rsc/machine/machines.csv`; this machine's binding to it: the gitignored `machine-name.txt` at the root (`yoga prerequisites` reports both)
- commit trailers (the `Signature:` grammar): `rsc/test/prepare-commit-msg-hook.sh` (the hook that stamps it)
- the forge's merge settings (server-side, so declared here as data): `src/main/cli/forge/forge.csv` (`yoga prerequisites` reconciles them against the live forge and prints each drift's own `gh` remedy)
- the checks: `src/test/dev/run.py` (`yoga test run`); cross-references: `yoga test xref` (bare `yoga test` shows status)

## Getting data

Bulk export: claude.ai → Settings → Data privacy controls → "Export data"; unzip
the emailed `data-*` into `data/input/claude/chat/bulk-export/`. Browser captures:
Safari logged in to claude.ai / gemini.google.com, then `yoga browser capture`
(or the macOS Shortcut: `open -a Terminal src/main/browser-captures/export.command`
— Terminal holds the folder permissions; Shortcuts' own shell is silently denied).
Code sessions: `yoga agent capture --all`. Paid model readings:
`yoga dashboard capture` (needs `ANTHROPIC_API_KEY` set; `yoga prerequisites`
reports it), rendered free by `yoga dashboard sync`. Batch disposal is computed, never assumed: `yoga supersede check`.

## Prerequisites

`jq` and Python 3; `./yoga pipeline run` creates the shared venv (`~/venvs/general`,
override via `VENV=`) and installs `src/requirements.txt`. Browser capture needs macOS + Safari. The repo ships no
data — `data/input/ tmp/cache/ data/output/ tmp/logs/` are git-ignored. Install the hook (required;
`yoga prerequisites` reports whether it is):
`./yoga test install-hook`. And the
signature hook (convention, optional; grammar in its own header):
the same `./yoga test install-hook` — it installs both.

## Changing it

Two audiences beyond the one this file addresses, and each has its own home. A
**developer** changes code and runs the hermetic gate — `src/test/dev/`, which needs no
network, no `gh` and no corpus, which is why the pre-commit hook can depend on it. An
**owner** merges, prunes, and keeps the forge's declared settings: `./CONTRIBUTING.md`.

## The public surface

Pages for <https://rpus.co> live under `rsc/site/`; deploy per `rsc/site/README.md`.

## Pre-public checklist

- [ ] Create a new repo (to get clean/sane git history).
- [ ] Add a LICENSE file.
- [ ] Make the README a tour: paired tell and show, the shown output derived so it cannot drift (#71's should — the maintainer's own task).
- [ ] `src/test/dev/schema_recommendations.py` — all 9 checks are stubbed; once implemented, call it from all pipeline `validate.sh` scripts on validation success
