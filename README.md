# corpus-yoga

Wrangles AI conversations — Claude (bulk export, browser capture, Claude Code
sessions) and Gemini (browser capture) — into one validated, readable, indexed
corpus.

## Quickstart

```bash
./src/main/cli/status/status.sh sync --apply   # pre-venv, once: mint the venv (bare, the same report read-only)
./corpus-yoga                        # suggests what to run next; runs none of it
./corpus-yoga status                 # read-only: whether everything is well, and what needs doing
./corpus-yoga walkthrough            # walk the room's state: n next, m members, v value, b back, x runs the command it stands on
./corpus-yoga browser capture        # acquire: Safari sweep into data/input/
./corpus-yoga pipeline run           # the usr gate: validate, extract, project (--plan previews)
./corpus-yoga server start --daemon  # read the corpus at http://localhost:8182
./corpus-yoga indexing capture       # PAID: the model re-reads the corpus for the index tables
./corpus-yoga site render            # render the corpus page from corpus + captures
./corpus-yoga test run               # the dev gate: the hermetic suite over src/ and rsc/
```

`./corpus-yoga -h` lists every command with its summary; `./corpus-yoga <command> -h` prints
the command's declaration - its forms, arguments and effects; `./corpus-yoga <command> <verb> --help` asks each target itself.

## The tiers

| root | lifecycle | medium | loss cost |
| --- | --- | --- | --- |
| `.` + `rsc/` + `src/` | machinery | git | none — clone again |
| `data/input/` | input | iCloud | none — as long as iCloud holds it |
| `tmp/cache/` | cache | local | none — `corpus-yoga cache sync` rebuilds it from the registry (`rsc/cache_io.csv`) |
| `tmp/stage/` | captured, rehearsed, not yet promoted | local | `input/`: a recapture — and, for a code session whose live log the provider has since expired, that session; `scratch/` and `rehearsal.json`: a rehearsal's derived tiers and its record of what it saw and judged, remade by `corpus-yoga pipeline rehearse`; `corpus-yoga stage clean` is the tier's janitor |
| `tmp/logs/` | run history | local | disposable |
| `data/output/` | historical accumulation | iCloud | the one irreplaceable tier — deposits, curation, readings |

A capture writes to `tmp/stage/input/`, at the address its unit will have under
`data/input/`, and reads nothing. The tiers are a declared contract (`src/main/tier.py`):
every script reads its data and tmp under one root, the checkout's, or the stage's
scratch, `tmp/stage/scratch/`, when `CORPUS_YOGA_REHEARSAL` names a rehearsal's stamp, and
`corpus-yoga pipeline rehearse` is the checkout's own code run under that name, its input
the shared `tmp/stage/input/`, judging the staged units there and writing the scratch
alone; what it saw and judged it then writes whole as the rehearsal record,
`tmp/stage/rehearsal.json` (`src/main/rehearsal.py`, its shape
`src/main/rehearsal.schema.json`), which the next rehearsal replaces and every promote
reads. Each capturing noun's `promote` verb - `corpus-yoga browser promote`,
`agent promote`, `export promote`, `forge promote`, over the same extent words as its
`capture` - is the one writer of `data/input/`, and it promotes a unit only where it
relates to the held one without loss - new, identical, extends, never ahead or diverged -
and every family its pipeline declares finds it valid at origin/main's version; the rest
it names (#687). Promotion is a copy: the stage is never written by it, and `corpus-yoga
stage clean` removes the units the store holds byte-equal.
So: `browser capture --provider claude`, `pipeline rehearse`, `browser promote
--provider claude`, `pipeline run chat-capture`; `corpus-yoga stage` reports the tier, and
each noun's bare status the units; `corpus-yoga store` reads shared storage in the same
terms - what is held, what is duplicated, and what the stage holds against it; each
tier's status compares the tier with the tier that feeds it, so the stage reads this
room's live stores and the store reads the stage (#842). The stage's cleaner looks forward,
at what the store already holds, and the store's inward.

Inputs are typed `data/input/<provider>/<channel>/<capture>/` — providers `claude`,
`gemini` have channels `chat`, `code` and captures `bulk-export`, `API-capture`,
`DOM-capture`, `machine-transport`; `github` has `forge` and `gh-CLI`. The readable corpus is
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
- every data shape: `rsc/schema/<writer>/[<provider>/]<family>/vN.json` - a family sits at the path of the code that writes against it under `src/main` (`pipeline/<pipeline>`, `cli/indexing`, `mcp`; `markdownConversation` at the root, its writer being `src/main/markdown_projection.py`), then the provider's name where its instances are one provider's, as `data/input` names them - history in its `CHANGELOG.md`, minting in `rsc/schema/WORKFLOW.md`; `corpus-yoga test run` holds the join (`check_schema_layout`)
- the cross-family model: `rsc/model/model.json`, the table of shared types across the families (name, description, occurrences), validated against the row shape `rsc/model/model.schema.json` beside it; `rsc/model/model_join.csv` the judged edges between families, `rsc/model/model_join_kinds.csv` their kinds, `rsc/model/model_rejected.txt` the rejections - curation in `rsc/schema/WORKFLOW.md`
- every upstream reference artefact: `rsc/reference/<project>/<lineage>/…`, byte-for-byte, every lineage upstream publishes (the MCP `schema.json` and `schema.ts` per dated lineage, the JSON Schema draft-04 meta-schema), each lineage with its own `CHANGELOG.md`, pinned by the `provenance.csv` beside them; `corpus-yoga reference` reports currency against upstream and `corpus-yoga reference sync` fetches
- the maintainer's own schema instruments, brought from the rpus repositories to read and judge the shapes above: `rsc/rpus/grammar/JSONSchema/draft04.g4` (the ANTLR grammar of draft-04 JSON Schema - a property named after a keyword is a name, never the keyword) and `rsc/rpus/grammar/TypeScript/` (the grammar of the TypeScript schema.ts speaks, its comments on a channel); the parsers ANTLR generates from them live under `src/gen/grammar/<project>/`, machine-local and gitignored, generated by `corpus-yoga grammar sync` (or `corpus-yoga status sync --apply`) with the tool and runtime `src/requirements.txt` pins - the mcp factoring is generated from schema.ts through the TypeScript one, upstream's schema.json its witness, and its consumer and producer faces derive from it under `tmp/cache/mcp/` and `rsc/rpus/documenter.json` (the documenter - a meta-schema of documented, non-degenerate definitions, stricter than draft-04's)
- naming vintages (as data): `rsc/naming/library_dir_vintages.csv`, `rsc/naming/memory_deposit_vintages.csv`
- the moves a rename owes the machine-local roots (data/output, tmp/cache, ext/mnt): `rsc/migration/<issue>.sh`, one per causing issue, guarded - `corpus-yoga migration` says each one's pending steps, `corpus-yoga migration sync --apply` takes them, and `corpus-yoga status` carries that status
- the provider registry: `rsc/provider/providers.csv` (the AI providers the repository knows, as data - what the commit hook attests and the machine report and mounts iterate)
- the machine registry: `rsc/machine/machines.csv`; this machine's binding to it: the gitignored `machine-name.txt` at the root (`corpus-yoga status` reports both)
- commit trailers (the `Signature:` grammar): `rsc/test/prepare-commit-msg-hook.sh` (the hook that stamps it)
- the forge's merge settings (server-side, so declared here as data): `src/main/cli/forge/forge.csv` (`corpus-yoga status` reconciles them against the live forge and prints each drift's own `gh` remedy)
- the checks: `src/test/dev/run.py` (`corpus-yoga test run`); cross-references: `corpus-yoga test xref` (bare `corpus-yoga test` shows status)

## Getting data

Bulk export: claude.ai → Settings → Data privacy controls → "Export data"; the
emailed link downloads a manifest, and `corpus-yoga export capture --manifest <file>`
stages it with the payload it lists. Browser captures:
Safari logged in to claude.ai / gemini.google.com, then `corpus-yoga browser capture`
(or the macOS Shortcut: `open -a Terminal src/main/cli/browser/capture.command`
— Terminal holds the folder permissions; Shortcuts' own shell is silently denied).
Code sessions: `corpus-yoga agent capture --all`; `corpus-yoga agent list-drafters` reads the Signatures on main against the sessions held. The forge's ledger (issues, pull
requests, comments, reviews, labels, blocked_by edges): `corpus-yoga forge capture` -
one stamped deposit under `data/input/github/forge/gh-CLI/` per run. Paid model readings:
`corpus-yoga indexing capture` (needs `ANTHROPIC_API_KEY` set; `corpus-yoga status`
reports it), rendered free by `corpus-yoga site render`. Disposal is computed, never assumed: `corpus-yoga store` reads what is duplicated, an earlier export held whole within a later one among it, and `corpus-yoga store clean` is its janitor.

## Prerequisites

`jq` and Python 3; `./src/main/cli/status/status.sh sync --apply` creates the
shared venv (`~/venvs/general`, override via `CORPUS_YOGA_VENV=`) and installs `src/requirements.txt` -
the one place the name `python3` survives (#478): `corpus-yoga` itself and every `.py` run in the venv. Browser capture needs macOS + Safari. The repo ships no
data — `data/input/ tmp/cache/ data/output/ tmp/logs/` are git-ignored. Install the hook (required;
`corpus-yoga status` reports whether it is):
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
