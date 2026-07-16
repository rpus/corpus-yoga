# claude-export-yoga

Wrangles AI conversations — Claude (bulk export, browser capture, Claude Code
sessions) and Gemini (browser capture) — into one validated, readable, indexed
corpus.

## Quickstart

```bash
./yoga prerequisites          # read-only: what this machine can run
./yoga browser capture        # acquire: Safari sweep into input/ (claude API; add --DOM for gemini)
./yoga run                    # process: validate, extract, project (--plan previews)
./yoga server start --daemon  # read the corpus at http://localhost:8182
./yoga check                  # the three-tier gate suite
```

`./yoga` lists every command with its summary; `./yoga commands [<command>]`
prints man entries; `./yoga <command> --help` asks each target itself.

## The tiers

| root | lifecycle | medium | loss cost |
| --- | --- | --- | --- |
| `.` + `rsc/` + `src/` | machinery | git | none — clone again |
| `input/` | input | iCloud | none — the medium carries it (sessions: once stashed via `yoga agent capture --all`) |
| `cache/` | cache | local | none — `yoga cache regen` rebuilds it from the registry (`rsc/cache_io.csv`) |
| `logs/` | run history | local | disposable |
| `output/` | historical accumulation | iCloud | the one irreplaceable tier — deposits, curation, readings |

Inputs are typed `input/<provider>/<channel>/<capture>/` — providers `claude`,
`gemini`; channels `chat`, `code`; captures `bulk-export`, `browser-API`,
`browser-DOM`, `machine-transport`. The readable corpus is
`output/markdown/<provider>/<channel>/`, and the pipelines never read
`~/.claude/projects` — sessions arrive via `yoga agent capture` through the
prefix-gated store.

## Where facts live

- the command surface: `rsc/cli/commands.csv` — grammar and gates: `rsc/cli/README.md`
- the doctrine (operations, laws L1–L8): `rsc/CALCULUS.md` (`yoga calculus`)
- every data shape: `rsc/schema/<pipeline>/<family>/vN.json`, history in its `CHANGELOG.md`, minting in `rsc/schema/WORKFLOW.md`
- naming vintages (as data): `rsc/naming/library_dir_vintages.csv`, `rsc/naming/memory_deposit_vintages.csv`
- machine manifests: `rsc/machines/` (`yoga machine`)
- the checks: `src/test/pre_commit.py` (`yoga check`); cross-references: `yoga xref`

## Getting data

Bulk export: claude.ai → Settings → Data privacy controls → "Export data"; unzip
the emailed `data-*` into `input/claude/chat/bulk-export/`. Browser captures:
Safari logged in to claude.ai / gemini.google.com, then `yoga browser capture`
(or the macOS Shortcut: `open -a Terminal .../src/main/browser-captures/export.command`
— Terminal holds the folder permissions; Shortcuts' own shell is silently denied).
Code sessions: `yoga agent capture --all`. Paid model readings:
`ANTHROPIC_API_KEY=... yoga dashboard capture`, rendered free by
`yoga dashboard present`. Batch disposal is computed, never assumed: `yoga supersede`.

## Prerequisites

`jq` and Python 3; `./RUNME.sh` creates the shared venv (`~/venvs/general`,
override via `VENV=`). Browser capture needs macOS + Safari. The repo ships no
data — `input/ cache/ output/ logs/` are git-ignored. Install the hook (gated,
required): `ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit`. And the
signature hook (convention, optional; `rsc/COMMITS.md`):
`ln -sfn ../../src/test/prepare_commit_msg.sh .git/hooks/prepare-commit-msg`.

## Contributing

Squash-only PRs, enforced by repository settings: main carries one narrated
commit per landed idea. If a PR can't be squashed, it was not atomic. Each commit
is signed `machine/provider/session` (the model dropped — it's derivable from the
session); grammar and rationale in `rsc/COMMITS.md`.

## The public surface

Pages for <https://rpus.co> live under `rsc/site/`; deploy per `rsc/site/README.md`.

## Pre-public checklist

- [ ] Create a new repo (to get clean/sane git history).
- [ ] Add a LICENSE file.
- [ ] `src/test/schema_recommendations.py` — all 9 checks are stubbed; once implemented, call it from all pipeline `validate.sh` scripts on validation success
