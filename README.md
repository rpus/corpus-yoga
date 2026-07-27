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
reports it), rendered free by `yoga dashboard sync`. Batch disposal is computed, never assumed: `yoga supersede check`.

## Prerequisites

`jq` and Python 3; `./yoga pipeline run` creates the shared venv (`~/venvs/general`,
override via `VENV=`) and installs `src/requirements.txt`. Browser capture needs macOS + Safari. The repo ships no
data — `data/input/ tmp/cache/ data/output/ tmp/logs/` are git-ignored. Install the hook (required;
`yoga prerequisites` reports whether it is):
`ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit`. And the
signature hook (convention, optional; grammar in its own header):
`ln -sfn ../../src/test/prepare_commit_msg.sh .git/hooks/prepare-commit-msg`.

## Contributing

Merge with `./yoga forge merge <pr>`. It reconciles the forge's settings against
`rsc/forge.csv` first and refuses on drift — so main's history is never composed by
rules nobody declared — and then squash-merges with **no message flags**, because
`squash_merge_commit_message: COMMIT_MESSAGES` is what assembles the body from the
branch's commits and keeps each one's `Signature:` line, the join key into the
captured session corpus. A hand-written `--body` discards them all.

`./yoga forge` alone is the read-only reconciliation, so a reviewer or a fresh cloner
can see what the forge does to a merge without having to merge one to find out; and
`./yoga forge sync --apply` makes the forge agree with `rsc/forge.csv` rather than
printing a `gh` command for someone to copy. It is `--apply`-gated because it writes
outside the repo, to a server other people see.

Squash-only PRs (enforced by forge settings). main carries one narrated commit per
landed idea; if a PR can't be squashed, it was not atomic. A branch may hold many
commits — the squash keeps every one of their messages and signatures.

An issue states what *should* be true; a PR that closes it reads as the claim that it
now is. Where that claim is a standing property the code must keep — not a one-off
change — make it a named check in `src/test/pre_commit.py`, labelled for the property
and the issue, so the PR asserts a compliance the gate can see and a later regression
trips a check that names what it broke. #22 is the worked example: the issue states the
`accumulate` contract, `rsc/CALCULUS.md` carries the sentence, and
`check_accumulate_contract` (labelled `accumulate: the CALCULUS trajectory contract
(#22)`) holds the code to it — its own commit verified it by breaking the rule and
watching the check fail. A guarantee whose only witness is a pull-request description is
not guarded.

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

A merge conflict is almost always confined to the check's four regenerated artifacts,
in two pairs — a derived file and the curated expectation beside it:

- `rsc/test/pre_commit.log` (derived) and `rsc/test/pre_commit_expected_checks` (curated)
- `rsc/test/xref.csv` (derived) and `rsc/test/xref_expected_score` (curated)

Do not hand-merge any of them, and do not compute the counts. Because `rsc/test/` holds
nothing but these four, the resolution is **syntactic** — take either side of the whole
directory (`git checkout --theirs rsc/test/`; the choice cannot matter) to clear the
markers, then run `./yoga check`: it rewrites the two derived files, and reports the
live counts the two curated ones should hold — `pre_commit` prints `expected X, got Y`,
`xref` shows the live counts in its own `xref: …` line. Set each curated file to what the
check reports, stage what it rewrote, and run once more to confirm the gate is green. The
check computes the merged numbers; your job is to run it.

This works because the generated files absorb only the counting. A real conflict — two
branches changing what a check *asserts* — lands in the source (`src/test/pre_commit.py`,
a schema file), where git makes you look at it, never inside `rsc/test/`. Since the
artifacts have their own directory now, the two cases are told apart by path: a conflict in
`rsc/test/` is syntactic; one outside it is real.

When a change's correctness depends on what a *fresh clone* sees — the expectation files
above, the xref counts, or anything deriving from `.gitignore` (the xref scan's skip-roots
do) — build it in a worktree outside the repo and run the gate from there rather than from
your working checkout. A checkout carries machine-local leftovers the scan can see; a fresh
worktree carries none, so the counts it reports are what a clone would report and not what
one disk happens to hold. It also keeps the evidence independent: the PR text asserts, the
diff shows, and the counts come from machinery that has read neither.

The corollary matters more than the technique: **never delete local files to make a gate
pass.** If a change would expose a machine's untracked leftovers to its own gate — dropping
an ignore rule does exactly that — say so in the pull request and let each machine clear its
own before the merge. Deleting state to get a green check destroys evidence and hides the
obligation from the room that owes it.

## The public surface

Pages for <https://rpus.co> live under `rsc/site/`; deploy per `rsc/site/README.md`.

## Pre-public checklist

- [ ] Create a new repo (to get clean/sane git history).
- [ ] Add a LICENSE file.
- [ ] `src/test/schema_recommendations.py` — all 9 checks are stubbed; once implemented, call it from all pipeline `validate.sh` scripts on validation success
