# The yoga CLI's command table

Two curated files describe the `./yoga` terminal surface (machinery: `src/main/cli/cli.py`;
launcher: the root `./yoga`). `commands.csv` names each command — `command,target,calculus,
step,summary` — and `help.csv` describes every argument, one row per
`command,subcommand,arg-name,arg-type,cardinality,help`. The argument structure lives ONLY
in `help.csv`: a command's verbs are its distinct subcommands, its flags are the `--arg-name`
rows, and its whole usage sketch is GENERATED from those rows — `arg-type` is the value
metavar (`<uuid8>`, blank for a boolean flag), and `cardinality` is a literal count: blank
is optional `[x]`; `1` is exactly one (required); `N/<class>` is N taken over the SET QUOTIENT
`<class>` — the mutually-exclusive args are one equivalence class (interchangeable in the slot
they fill), so `1/agent-capture-1` is cardinality-1 in the quotient by that class, rendered as
the exclusive choice `(a | b)`. The class is named `<command>-<subcommand>-<ordinal>`. So the usage
cannot drift from the helptext, because there is one source, not two — nothing to reconcile,
no check. A flag is scoped to its verb (`cache`'s `--dry-run` lists orphans under `clean`,
prints producer commands under `sync`); `subcommand` blank is command-level, `arg-name` blank
describes the verb itself. Both files are written `QUOTE_ALL` so a comma in any cell is safe.

Everything a user meets is re-derived on demand — the menu `./yoga -h`
prints, each command's `./yoga <command> -h` (its summary, its generated invocation forms, and the
`help.csv` lines as headed subparagraphs), the zsh tab-completion `./yoga completions` emits
— and stored nowhere, because presentation is never load-bearing (L5 of `rsc/CALCULUS.md`).
`./yoga <command> [args...]` execs the row's target with the args forwarded verbatim; a bare
`./yoga` runs the machine report (`yoga prerequisites`), and a verb's own flags live one
level down at `./yoga <command> <verb> -h`, which passes through to the target's argparse.
That argparse carries no help strings of its own; `src/main/argparse_help.py` fills them from
`help.csv` each time the target runs, so the target's own `-h` reads the same wording whether
reached via `yoga` or run directly — one source for the words, argparse still the authority on structure.

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
  what `input/` already holds. `present` renders, free. `clean`/`sync` are the
  cache lifecycle. `receive`/`demerge` move agents between machines and undo the move.
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

## Held honest by the gates

`check_cli_surface` (pre-commit code tier — its docstring is the authority) holds
every row to: parseable table, unique + alphabetical commands, existing targets,
calculus terms defined in `rsc/CALCULUS.md`, advertised flags present in the
target, the target's own flags all advertised back (both directions), advertised
verbs in the target's live `--help`, help ≤ 20 lines, claimed run-steps named in
`RUNME.sh --plan`, and the emitted completion parsing under `zsh -n`.

The table is curated, not discovered: a script's absence here is a decision, not
an omission.
