# The yoga CLI's command table

Two curated files describe the `yoga` terminal surface (machinery: `src/main/cli/cli.py`;
launcher: the root `yoga`). `commands.csv` names each command — `command,target,calculus,
summary` — and `help.csv` describes every argument, one row per
`command,subcommand,arg-name,arg-type,cardinality,help,step`. The argument structure lives ONLY
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
describes the verb itself. The `step` column, set on a verb's own row, marks that invocation
as a step of the named run pipeline (`chat-exports`), or of the root RUNME's whole-corpus
tail (`corpus`) — the reduce that runs once (after every pipeline, for an operation whose
input spans them all): the gate holds `src/RUNME.sh --plan` to
invoking it by command AND verb, so the plan speaks the surface you would type and a step can
never drop to a bare noun (which the bare=status convention would silently make a no-op). Both
files are written `QUOTE_ALL` so a comma in any cell is safe.

Everything a user meets is re-derived on demand — the menu `yoga -h`
prints, each command's `yoga <command> -h` (its summary, its generated invocation forms, and the
`help.csv` lines as headed subparagraphs), the zsh tab-completion `yoga completions` emits
— and stored nowhere, because presentation is never load-bearing (L5 of `rsc/CALCULUS.md`).
`yoga <command> [args...]` execs the row's target with the args forwarded verbatim; a bare
`yoga` runs the machine report (`yoga prerequisites`), and a verb's own flags live one
level down at `yoga <command> <verb> -h`, answered by argparse — the target's own, or the
parser `cli.py` builds for a command it handles itself.
That argparse carries no help strings of its own; `src/main/argparse_help.py` fills them from
`help.csv` each time the target runs, and names the parser for the command rather than the file
implementing it (`usage: yoga agent capture`, never `agent.py capture`), so the target's own `-h`
reads the same wording whether reached via `yoga` or run directly — one source for the words,
argparse still the authority on structure.

Two commands produce/consume corpus *readings* whose file formats are a contract but whose
data lives outside git (durable in `data/output/`, rebuildable in `tmp/cache/`): `yoga dashboard` (model
captures) and `yoga indexing` (user curation). Their format spec and the disposal loop are
committed in `rsc/cli/readings.md`.

## Columns

| column | meaning |
| --- | --- |
| `command` | the subcommand word (`yoga <command>`), unique |
| `target` | repo-relative file the command execs: a `.sh` (or extensionless script) runs directly, a `.py` runs via `src/run_python_script.sh`, a `.md` is printed |
| `calculus` | space-separated operations and laws from `rsc/CALCULUS.md` that the command performs; empty where the command is mere presentation of the doctrine itself |
| `summary` | one line, used in help and as the completion description (keep it free of quotes) |

The argument sketch and each command's verbs, flags, and run-pipeline `step` all live in
`help.csv` (above), never here — one source, nothing to reconcile.

## The grammar

The laws governing the CLI — the table, and the tree it points into — stated once and
machine-read. `grammar_laws()` in `src/main/cli/cli.py` parses every `**G<n> — …**` lead
below, exactly as `calculus_terms()` parses `rsc/CALCULUS.md`; a check cites the law it
enforces (`run(..., law='G4')`) and cannot cite a law this document does not state.

Each law carries its enforcement state, so an unenforced law is visible rather than
absent:

| state | meaning |
| --- | --- |
| `gated` | at least one check cites it; a violation vetoes the commit |
| `by construction` | the shape makes violation impossible — there is no second source to check |
| `unenforced (#N)` | stated but not yet held; the issue that will hold it |
| `doctrine` | stated deliberately with no check: none is feasible, or none is worth its cost |

A law may also carry `from L<n>`: it is a corpus law (`rsc/CALCULUS.md`) applied to the
surface, and that document is the authority for the principle — cited, never paraphrased.
G3 is L5 (presentation is re-derivable) applied to usage; G10 implements L9's `run`-step
mechanism; G1's `sync` clause is L1; G16 is bounded by L2, which is why a plan line must
name a REPO-RELATIVE path (an absolute one would put a machine fact in a committed
artifact). The cited law must exist in `rsc/CALCULUS.md` — `check_grammar_laws` holds it.

`check_grammar_laws` holds this both ways: every citation names a stated law, and every
`gated` law is really cited by a check that ran. So the enforcement map is derived from
the laws rather than maintained as prose beside them.

Ids are permanent, assigned when a law is first stated, so they need not run in document
order: a law is cited by id, and moving it in the text must never change what a check cites.

A law marked `doctrine` is not a gap awaiting a check. Three of these — a verb's single
meaning, a comment's obligation, a command word's part of speech — could only be checked by
first curating a vocabulary to check against, which is maintenance added to police prose.
They are stated, followed, and reviewed by people.

### The table

- **G1 — A verb means one thing everywhere it appears.** `doctrine (#49)` `from L1` — `capture` acquires
  (`browser capture`, `dashboard capture`, `agent capture` all *bring data in*, from
  Safari, the paid model, and the harness's session store); `sync` regenerates
  idempotently; `clean` destroys; `run` only processes what `data/input/` already holds;
  `present` renders, free; `receive`/`demerge` move agents between machines and undo the
  move.
- **G2 — Bare is status: free, local, and read-only.** `unenforced (#47, #52)` — never paid,
  never a browser. Bare is a *read-only status report* wherever the command has verbs, the
  write living in the verb (`dashboard`, `indexing`, `server`, `memories`, `summaries`,
  `model`, `supersede`, `xref`); the command's *whole act* where it has no verb and that
  act is one free idempotent step (`check`, `prerequisites` — `run` left this set when it
  became `pipeline run`, and #40 takes `check` to `test run`, leaving `prerequisites` alone
  or nothing); and a *usage refusal* where the verb is required
  and bare is meaningless (`browser`, `cache`, `agent`).
- **G19 — An effecting verb is bracketed by status.** `doctrine (#56)` — it reports the
  state it is about to change, then effects, then reports the state it left. The bracket is
  what makes an effect auditable without a log, and what stops a verb reporting success it
  has not earned: `yoga dashboard capture` prints an exact coverage join before spending and
  nothing after, so a reading covering 125 of 137 conversations was promoted behind a ✓ that
  counted rows. Stated first, and for a long time only, as a parenthetical in
  `src/main/chat-exports/dashboard.sh` — the same file that implements half of it.
- **G3 — Usage is a small grammar.** `by construction` `from L5` — a spaced ` | ` separates
  INVOCATION FORMS, each becoming its own line in `yoga commands` and its own verb for the
  honesty gate; an unspaced `|` is an enum inside one form (`--provider claude|gemini`);
  parens group a required choice (`(--dry-run|--apply)`); brackets mark the optional. The
  usage sketch is GENERATED from `help.csv`, so there is no second source to reconcile.
  The completion offers `--flags` at VERB scope — exactly the verb's own rows, never the
  across-verbs union, which would TAB-complete flags the dispatched verb rejects;
  command-level rows (`subcommand` blank) complete only before a verb, where argparse
  accepts them.
- **G4 — The table is unique and ordered.** `gated` — command words are unique and rows
  alphabetical, so every derived surface lists commands in one findable order.
- **G5 — What the table advertises, the target accepts; and what the target accepts, the
  table advertises.** `gated` — both directions, against the target's live `--help` rather
  than a source grep: an advertised verb must really be dispatched, an advertised flag must
  really be accepted (including by the verb, not merely by the command parser), and a flag
  the target declares must be advertised back.
- **G6 — A row cites only defined vocabulary.** `gated` — every term in the `calculus`
  cell is defined in `rsc/CALCULUS.md`, which is parsed as the authority rather than
  restated here.
- **G7 — A command's target exists.** `gated` — and #40 strengthens this: the target's
  stem must equal the command word, so the column becomes verification rather than
  curation.
- **G8 — Help is bounded: one screen, one shape.** `gated` — name, what, usage, flags, in
  ≤ 20 lines. Essays live in changelogs.
- **G9 — The emitted completion is a program, and must parse.** `gated` — `zsh -n` over
  what the install ritual writes.
- **G10 — A `step`-marked command is a corpus-wide operation, invoked by command and
  verb.** `gated` `from L9` — never a per-batch one. The chat-exports pipeline is a map over batches
  (`run_one`) then a reduce over all of them (`run_tail`); the nouns live only in the
  reduce, because only a whole-corpus step is meaningful to invoke standalone. `memories`,
  `summaries`, `supersede` are exactly the `run_tail` steps, and the plan must name each
  by command AND verb — a bare noun would silently be a status no-op under G2.
- **G20 — What a command installs outside the repo is identified by a stable token, and
  every instance of it is removed.** `gated` `from L1` — the marker delimiting an installed
  block carries advice to the reader, and advice is edited; identity is the part that must
  not be. Matching the whole line made a wording change (`./yoga` → `yoga`) orphan every
  block the earlier version had written: install inserted a second beside it, uninstall
  could not remove it, and status called a wired shell unwired. Convergence therefore
  removes EVERY recognised block, not the first — removing one and writing one is not
  idempotence when two exist, and the survivor's `fpath` entry shadows the current one.
- **G21 — A flag never names a value of an axis the command already has.** `gated` — an
  axis is a restriction (`--mechanism API|DOM`) and a flag named for one of its values reads
  as a restriction to it while behaving as an addition. `--DOM` meant "also walk the DOM",
  so the only restriction anyone wanted — API alone, skip the walk — was unsayable, and the
  default it would have named was hard-coded instead. Both flags are now restrictions on
  independent axes, and the run is their intersection; an empty intersection is reported,
  never quietly replaced by a default.

### The tree

The laws above govern the rows. These govern what the rows point into, and are stated
here so that a check can cite them as they land (see #39).

- **G11 — A command determines its target's name, and a file is named for the operation it
  performs.** `unenforced (#40)` — never for its caller, its occasion, or its reader.
  `yoga <noun> <verb>` ⇒ `<noun-dir>/<verb>.<ext>`.
- **G12 — A file lives at the level of its subject.** `unenforced (#41)` — a module used
  from more than one tier lives above them; one used within a tier lives in it.
- **G13 — Help is the table, rendered once.** `unenforced (#42)` — no target renders help
  of its own, in any language.
- **G14 — A name is derived from what it denotes, and one referent has one name.**
  `unenforced (#43)` — a path constant is named for the tail of the path it holds.
- **G15 — A comment states a constraint that an otherwise-correct edit would violate.**
  `doctrine (#44)` — and never asserts a date or a count. History goes to the changelog.
- **G16 — A printed line names both sides concretely.** `unenforced (#45)` `from L2` — a plan line
  names its operation, whether it is typeable, and the file it lives in; no line stands in
  for something it does not name.
- **G17 — The only invocation any output or document prescribes is a `yoga` command.**
  `unenforced (#46)` — never `run_python_script.sh`, never a script path.
- **G18 — Every command is a noun.** `doctrine (#47)` — `run` became `pipeline run`; `check` and `xref` remain, and #40 takes them to `test`. — no command word is a verb, and
  no flag names what the command grammar already addresses as a noun.

The table is curated, not discovered: a script's absence here is a decision, not
an omission.
