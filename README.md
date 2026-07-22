# claude-export-yoga

Wrangles AI conversations — Claude (bulk export, browser capture, Claude Code
sessions) and Gemini (browser capture) — into one validated, readable, indexed
corpus.

## Quickstart

```bash
./yoga prerequisites          # read-only: what this machine can run
./yoga browser capture        # acquire: Safari sweep into data/input/ (claude API; add --DOM for gemini)
./yoga run                    # process: validate, extract, project (--plan previews)
./yoga server start --daemon  # read the corpus at http://localhost:8182
./yoga check                  # the three-tier gate suite
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

- the command surface: `rsc/cli/commands.csv` (arguments: `rsc/cli/help.csv`) — grammar and gates: `rsc/cli/README.md`
- the doctrine (operations, laws L1–L8): `rsc/CALCULUS.md` (`yoga calculus`)
- every data shape: `rsc/schema/<pipeline>/<family>/vN.json`, history in its `CHANGELOG.md`, minting in `rsc/schema/WORKFLOW.md`
- naming vintages (as data): `rsc/naming/library_dir_vintages.csv`, `rsc/naming/memory_deposit_vintages.csv`
- the machine registry: `rsc/machine/machines.csv`; this machine's binding to it: the gitignored `machine-name.txt` at the root (`yoga prerequisites` reports both)
- commit trailers (the `Signature:` grammar): `src/test/prepare_commit_msg.sh` (the hook that stamps it)
- the forge's merge settings (server-side, so declared here as data): `rsc/forge.csv` (`yoga prerequisites` reconciles them against the live forge and prints each drift's own `gh` remedy)
- the checks: `src/test/pre_commit.py` (`yoga check`); cross-references: `yoga xref check` (bare `yoga xref` shows status)

## Getting data

Bulk export: claude.ai → Settings → Data privacy controls → "Export data"; unzip
the emailed `data-*` into `data/input/claude/chat/bulk-export/`. Browser captures:
Safari logged in to claude.ai / gemini.google.com, then `yoga browser capture`
(or the macOS Shortcut: `open -a Terminal src/main/browser-captures/export.command`
— Terminal holds the folder permissions; Shortcuts' own shell is silently denied).
Code sessions: `yoga agent capture --all`. Paid model readings:
`yoga dashboard capture` (needs `ANTHROPIC_API_KEY` set; `yoga prerequisites`
reports it), rendered free by `yoga dashboard sync`. Batch disposal is computed, never assumed: `yoga supersede`.

## Prerequisites

`jq` and Python 3; `./src/RUNME.sh` creates the shared venv (`~/venvs/general`,
override via `VENV=`). Browser capture needs macOS + Safari. The repo ships no
data — `data/input/ tmp/cache/ data/output/ tmp/logs/` are git-ignored. Install the hook (required;
`yoga prerequisites` reports whether it is):
`ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit`. And the
signature hook (convention, optional; grammar in its own header):
`ln -sfn ../../src/test/prepare_commit_msg.sh .git/hooks/prepare-commit-msg`.

## Contributing

Before merging anything, run `./yoga prerequisites`: it reconciles the forge's
settings against `rsc/forge.csv` and prints the `gh` command for any drift, so a
reviewer or a fresh cloner can see what the forge actually does to a merge without
having to merge one to find out.

Squash-only PRs (enforced by forge settings; `./yoga prerequisites` reconciles
them against `rsc/forge.csv`). main carries one narrated commit per landed idea;
if a PR can't be squashed, it was not atomic.

Merge with the bare command — **no message flags**:

```bash
gh pr merge <n> --squash
```

Do NOT pass `--subject` or `--body`. The forge sets `squash_merge_commit_message:
COMMIT_MESSAGES`, so GitHub composes the squash commit from the branch's commit
messages — which carry each `Signature:` trailer. A custom body overrides that
composition: the signature never reaches main, and the `Co-Authored-By` line the
commit hook strips locally survives instead — an unsigned, co-authored commit on
main. Write the record in the commits; the pull-request description is review
conversation, not the record.

Every commit is signed `Signature: machine/provider/session` by the local
`prepare-commit-msg` hook (`src/test/prepare_commit_msg.sh`), which also drops the
model co-author (it is derivable from the session).

## The public surface

Pages for <https://rpus.co> live under `rsc/site/`; deploy per `rsc/site/README.md`.

## Pre-public checklist

- [ ] Create a new repo (to get clean/sane git history).
- [ ] Add a LICENSE file.
- [ ] `src/test/schema_recommendations.py` — all 9 checks are stubbed; once implemented, call it from all pipeline `validate.sh` scripts on validation success
