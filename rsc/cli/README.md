# The yoga CLI's command table

`commands.csv` is the single authority for the `./yoga` terminal surface (machinery:
`src/main/cli/cli.py`; launcher: the root `./yoga`). Everything a user meets is re-derived
from this table on demand — the help text a bare `./yoga` prints, the zsh tab-completion
`./yoga completions` emits — and stored nowhere, because presentation is never load-bearing
(L5 of `rsc/CALCULUS.md`). The CLI adds no behaviour of its own: `./yoga <command> [args...]`
execs the row's target with the args forwarded verbatim, so `./yoga <command> --help` prints
the *target's* help and each script remains the one authority on its own interface.

Two commands produce/consume corpus *readings* whose file formats are a contract but whose
data lives outside git (durable in `output/`, rebuildable in `cache/`): `yoga dashboard` (model
captures) and `yoga indexing` (user curation). Their format spec and the disposal loop are
committed in `rsc/cli/readings.md`.

## Columns

| column | meaning |
| --- | --- |
| `command` | the subcommand word (`./yoga <command>`), unique |
| `target` | repo-relative file the command execs: a `.sh` (or extensionless script) runs directly, a `.py` runs via `src/run_python_script.sh`, a `.md` is printed |
| `usage` | human-readable argument sketch shown in help; its `--flags` are also machine-read, both for completion and for the honesty check below |
| `calculus` | space-separated operations and laws from `rsc/CALCULUS.md` that the command performs; empty where the command is mere presentation of the doctrine itself |
| `step` | the `RUNME.sh --plan` step this command re-runs standalone (empty where none); each value is checked to name a real plan step |
| `summary` | one line, used in help and as the completion description (keep it free of quotes) |

## The grammar

Rules that govern every row, stated once (a reader should never have to infer them
from examples — one did, and misread design as sediment):

- **Verbs.** `capture` is the acquisition verb everywhere it appears — `browser
  capture`, `dashboard capture`, `agent capture` all *bring data in* (from Safari,
  the paid model, the harness's session store respectively). `run` only processes
  what `input/` already holds. `present` renders, free. `clean`/`regen` are the
  cache lifecycle. `receive`/`demerge` move agents between rooms and undo the move.
- **Bare invocations are free and local** — never paid, never a browser. Bare is a
  *status report* where the summary says so (`dashboard`, `indexing`, `server`);
  the command's *whole act* where that act is one free idempotent step (`run`,
  `memories`, `supersede`, `model`, `check`, `xref`, `prerequisites`); and a
  *usage refusal* where a verb is required (`browser`, `cache`, `agent`).
- **Usage strings are a small grammar, machine-read.** A spaced ` | ` separates
  INVOCATION FORMS — each becomes its own line in `yoga commands` and its own
  verb for the honesty gate. An unspaced `|` is an enum inside one form
  (`--provider claude|gemini`). Parens group a required choice
  (`(--dry-run|--apply)`); brackets mark the optional. `--flags` are harvested
  across all forms and deduplicated for the completion.
- **Rows are alphabetical by command**, enforced (`cli: commands alphabetical`),
  so every derived surface lists commands in one findable order.

## The table speaks the calculus, and is held to it

Each row cites the calculus operations and laws its command performs, so the help text
doubles as a map from the terminal surface onto `rsc/CALCULUS.md` — showing and telling
the calculus. The pre-commit **code tier** (`check_cli_surface` in `src/test/pre_commit.py`)
keeps the telling honest, deterministically on any clone:

- the table parses and command names are unique;
- every `target` exists;
- every term in a `calculus` cell is defined in `rsc/CALCULUS.md` — the vocabulary is
  parsed from the document's own operation/law bullets, never restated elsewhere;
- every `--flag` a `usage` sketch advertises appears in the target's source, or in its
  stem-sibling `.py`/`.sh` pair (wrapper and implementation share a stem — the repo idiom).

The table is curated, not discovered: it is the repo's chosen presentation surface, so a
script's absence here is a decision, not an omission. Operations without a command
(e.g. atomise, which lives inside `./yoga run`'s steps) are likewise partiality, not gaps.

## Flags and steps correspond, in three tiers of authority

How do RUNME flags relate to yoga invocations? Three correspondences, none of them a
hand-maintained table:

1. **Flags are the identity map.** Dispatch execs the target with args forwarded
   verbatim, so `./yoga run --plan` ≡ `./RUNME.sh --plan` for every flag, by
   construction — a correspondence table would imply it could be otherwise.
2. **Flag → step is printed by the plan itself.** `./yoga run --plan` annotates every
   conditional step with the flag or condition that enables it (`compare_sources
   (only when live captures exist)`), and the plan is the executing step list
   (`src/main/steps.sh`), so this correspondence cannot drift.
3. **Step → standalone command is the `step` column.** Where a plan step can be
   re-run on its own, the row says so (`./yoga memories` ≡ run step
   `accumulate_memories`; `./yoga supersede` ≡ `compare_batches`), the help renders it,
   and `check_cli_surface` verifies each claimed step names a real step in the
   `RUNME.sh --plan` output — closing the chain: execution = plan ⊇ table.

## Issues speak yoga

The table also gives *problem reports* a stable, in-band vocabulary: a repo or
project issue should be succinctly specifiable as yoga commands — the command
line that exhibits it, what was expected, what was observed. `./yoga supersede`
exits 1 on a batch believed superseded; `./yoga check` disagrees with the
committed log; `./yoga indexing build` drops a locator that `./yoga server` can reach. An
issue that cannot be phrased as commands plus data is probably not yet
understood — and one that can is reproducible from the repo by construction,
on any machine, which is the same property demanded of every process here.

## Commands

    ./yoga                        # render the table as help
    ./yoga completions             # zsh completion script to stdout
    ./yoga completions --write     # write it under cache/ and print the ~/.zshrc lines to add
    ./PREREQUISITES.sh            # reports (read-only) whether this machine has completion generated, current, and wired
