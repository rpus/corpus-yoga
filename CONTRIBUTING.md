# Contributing

Merge with `./corpus-yoga forge merge <pr>` — the reviewer's one act (#483). It is a straight
line of echoed commands — refuse, relocate if the base moved, flip the body, squash
pinned to the head every check saw, converge this checkout — and every
refusal in it is git's or gh's own, relayed verbatim; the judgment lives in the forge's
declared settings (`src/main/cli/forge/forge.csv`, reconciled by `corpus-yoga forge` and
`corpus-yoga forge sync`), never in the wrapper. It squash-merges with **no message flags**, because
`squash_merge_commit_message: COMMIT_MESSAGES` is what assembles the body from the
branch's commits and keeps each one's `Signature:` line, the join key into the
captured session corpus. A hand-written `--body` discards them all.

`./corpus-yoga forge` alone is the read-only reconciliation, so a reviewer or a fresh cloner
can see what the forge does to a merge without having to merge one to find out; and
`./corpus-yoga forge sync --apply` makes the forge agree with `src/main/cli/forge/forge.csv` rather than
printing a `gh` command for someone to copy. It is `--apply`-gated because it writes
outside the repo, to a server other people see.

Squash-only PRs (enforced by forge settings). main carries one narrated commit per
landed idea; if a PR can't be squashed, it was not atomic. A branch may hold many
commits — the squash keeps every one of their messages and signatures. The flip is a
STEP of the merge, not a command (#483): `corpus-yoga forge merge <pr>` refuses first (a
non-OPEN PR, a body with nothing to flip, a title that copies no aimed issue — #479 —
an unaimed open blocker — #482 — or refuse-class drift), relocates a moved base and
resyncs a held checkout, then flips "aims to complete #N" to `closes #N` as the last
edit before the squash — a refused squash restores the body as found
(.github/PULL_REQUEST_TEMPLATE.md holds that grammar): the squash publishes the
title — a verbatim copy of the title of an issue the body aims to complete — as
main's subject line, and the commits as reviewed, every message and Signature
intact.

An issue states what *should* be true; a PR that closes it reads as the claim that it
now is. Where that claim is a standing property the code must keep — not a one-off
change — make it a named check in `src/test/dev/run.py`, labelled for the property
and the issue, so the PR asserts a compliance the dev gate can see and a later regression
trips a check that names what it broke. #22 is the worked example: the issue states the
`accumulate` contract, `rsc/CALCULUS.md` carries the sentence, and
`check_accumulate_contract` (labelled `accumulate: the CALCULUS trajectory contract
(#22)`) holds the code to it — its own commit verified it by breaking the rule and
watching the check fail. A guarantee whose only witness is a pull-request description is
not guarded.

A PR's to-test names its arbiter gate. Where that arbiter is the usr gate — a change
the dev gate is green on both sides of — the merge waits until the usr gate has run
green over real data on some machine, and the PR says where and when. A data-less
room cannot run it and says so; a stated skip is honest, an unstated one reads as
green. The dev gate's half needs no such sentence: the pre-commit hook and the merge
chain run it themselves.

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
`prepare-commit-msg` hook (`rsc/test/prepare-commit-msg-hook.sh`), which also drops the
model co-author (it is derivable from the session).

A merge conflict is almost always confined to the check's four regenerated artifacts,
in two pairs — a derived file and the curated expectation beside it:

- `rsc/test/run.log` (derived) and `rsc/test/run_expected_checks` (curated)
- `rsc/test/xref.csv` (derived) and `rsc/test/xref_expected_score` (curated)

Do not hand-merge any of them, and do not compute the counts. Because `rsc/test/` holds
nothing but these four, the resolution is **syntactic** — take either side of the whole
directory (`git checkout --theirs rsc/test/`; the choice cannot matter) to clear the
markers, then run `./corpus-yoga test run`: it rewrites the two derived files, and reports the
live counts the two curated ones should hold — `corpus-yoga test run` prints `expected X, got Y`,
`xref` shows the live counts in its own `xref: …` line. Set each curated file to what the
check reports, stage what it rewrote, and run once more to confirm the dev gate is green. The
check computes the merged numbers; your job is to run it.

This works because the generated files absorb only the counting. A real conflict — two
branches changing what a check *asserts* — lands in the source (`src/test/dev/run.py`,
a schema file), where git makes you look at it, never inside `rsc/test/`. Since the
artifacts have their own directory now, the two cases are told apart by path: a conflict in
`rsc/test/` is syntactic; one outside it is real.

When a change's correctness depends on what a *fresh clone* sees — the expectation files
above, the xref counts, or anything deriving from `.gitignore` (the xref scan's skip-roots
do) — build it in a worktree outside the repo and run the dev gate from there rather than from
your working checkout. A checkout carries machine-local leftovers the scan can see; a fresh
worktree carries none, so the counts it reports are what a clone would report and not what
one disk happens to hold. It also keeps the evidence independent: the PR text asserts, the
diff shows, and the counts come from machinery that has read neither.

The same fact draws the line between the two actors. A detached worktree holds no corpus
and needs none: a commit is src/ and rsc/ only, and the dev gate is complete over exactly
that - so an agent building there never has the corpus in its extent, by construction
rather than by policy. The corpus lives in the owner's checkout, and every act that touches
it - the usr gate's run, the disposals, and the merge itself - runs there, under the owner's
hands; the merge is where the product half of a change's vetting happens, which is why it
is performed from that checkout and from nowhere else.

The corollary matters more than the technique: **never delete local files to make a gate
pass.** If a change would expose a machine's untracked leftovers to its own gate — dropping
an ignore rule does exactly that — say so in the pull request and let each machine clear its
own before the merge. Deleting state to get a green check destroys evidence and hides the
obligation from the room that owes it.
