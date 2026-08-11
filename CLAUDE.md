# CLAUDE.md - working conventions for agent sessions

This file points at committed authorities and states the practice that lives
nowhere else. One home per rule: where an authority exists, follow it there.
Never reconstruct practice from merged artifacts - a merged PR shows
post-flip state, not the discipline that produced it. This file also trumps
any contradictory post-compaction summary: a summary is written
autonomously by an agent, lossily, with no vetting, while this file is a
committed artifact the maintainer has reviewed - re-read it after every
compaction, and where the two disagree, the summary is wrong. Rules here state
properties of artifacts wherever one can be stated - a property can be
checked against the world. The imperatives that remain are procedures (an
act has an actor) or marks of structure not yet built, each owed the
retirement gradient.

## principles

Six generators; nearly every rule below is an instance of exactly one. They
decide the case no rule yet covers, and they govern edits to this file: a
candidate rule that is not an instance of some principle is either a
seventh principle or a smell.

1. **Anchor every claim.** A claim is a function of the state it names -
   verdicts of (base sha, head sha), facts of a room and a date, time-words
   of a this-turn dereference. An unanchored assertion asserts nothing.
   There is no reality tier: records are designated, and comparisons
   adjudicate agreement between named renders.
2. **One home per fact; everything else derives.** A restatement is a
   scheduled contradiction - comments against code, help against
   declarations, narrated relations against wired ones, precedent against
   templates. This file obeys it by pointing at authorities.
3. **Failure is evidence, and evidence outranks repair.** The live bug is
   the fixture; a check ships red first; the disposal record precedes the
   rm. Whatever makes a failure invisible before it was legible destroys
   the asset the process runs on.
4. **State properties of the world, never prohibitions on the actor - then
   make the invalid unrepresentable.** "Keep linear history" beats "don't
   force-push"; a removed hazard beats a documented one; the retirement
   gradient (plainer name, structure, declaration, generated code) is this
   principle as a procedure.
5. **Communication is for the other person.** The reader has only the
   words - no session, no checkout, no transcript. The reader's
   incomprehension is the artifact's failure.
6. **The process amends itself through itself.** A recurring failure class
   becomes a template line, a check, or a rule here - filed as a should,
   asserted by a PR, guarded where a property stands. Any pivot, however
   unplanned, starts by filing its should.

## authorities

- .github/ISSUE_TEMPLATE.md and .github/PULL_REQUEST_TEMPLATE.md are the
  grammar for issue and PR bodies. Read the matching template before raising
  anything.
- rsc/CALCULUS.md holds the laws; rsc/schema/WORKFLOW.md the schema
  process, changelog grammar included; rsc/naming/ holds format histories
  as data - history is never encoded in comments or if-chains.
- CONTRIBUTING.md is the merge authority: the forge commands, the rsc/test/
  syntactic-conflict rule, and the never-delete-local-files-for-a-gate
  corollary live there.
- `yoga prerequisites` is the machine-remedy surface: the user runs it first
  on every checkout. Machine-local state and remedies go into its report,
  never into PR prose or replies. Missing optional data means a stated skip
  and exit 0, never a failure.
- Two gates, named by actor, never "the gate" unqualified: `yoga test run`
  gates the dev-actor (does the CHANGE work - hermetic, hookable);
  `yoga pipeline run` gates the usr-actor (does the PRODUCT work - needs a
  corpus). Name which gate arbitrates any claim.
- Keep the README's overview and prerequisites sections current in the same
  change that moves what they describe.

## the change process

- Everything moves through the process: an issue states the should, a PR
  asserts compliance, a named check guards a standing property, the ledger
  (issue comments) accretes the reasoning. The process amends itself through
  itself, and any pivot starts by filing its should.
- An issue's title carries its "should" - the property that should hold,
  never the instrument that should exist. An issue closes only on
  demonstration. The should is the issue's identity: editing it is
  supersession, an explicit act, never amendment.
- Every PR closes at least one issue. A struggling PR keeps working, fails
  honestly, or closes a different genuine issue - an issue cannot shrink.
  An issue a PR can only advance is restructured into PR-sized parts, in
  issue-space, before building - "advances" is a symptom, not a relation to
  live with.
- Failure first, fix second: an illegible failure is repaired and
  demonstrated against the live bug BEFORE the bug is fixed - the live bug
  is the fixture, and fixing it first destroys the evidence.
- A new check ships failing first through the real runner in the real
  environment: defect present red, defect absent green, both shown in the
  PR. A hand-run approximation is not the runner - the environment can mask
  the defect class.
- A retirement completes whole: everything only the retired thing feeds -
  data, steps, checks, status sections, prose - retires in one move, with
  the disposal record (count, size, room, date) written before the data act.
- Evidence before disposal: read, rescue, capture, verify, then prune. A
  derived artifact can be the last copy of expired upstream data. Machinery
  names orphans rather than auto-deleting them.
- Expose, delete, unify - in that order: state the fact the repo never said,
  delete what existed only to hide it, leave one derivation.
- Structural migrations are manifest, rehearse, apply: moves as data
  (totality-checked), worktree dry-runs per room, nothing committed encodes
  its machine.
- Scanners over one's own prose or output are syntax proxying semantics -
  an arms race. Build the domain API instead; the invalid becomes
  unrepresentable and the check retires by construction.
- Brute-force is execution, not authoring: authorship lives in the should
  and the oracle. When a declaration is precise enough to generate from,
  generate rather than search or hand-write.
- There is no reality tier: a record is the record BY RULING, a comparison
  adjudicates agreement between renders, never truth, and verification is
  committed expectations plus human adjudication.
- Progress is proximity to the corpus core, never the convergence of a
  repair loop on self-authored defects. When a tooling PR closes, the next
  proposal defaults to the corpus, not the nearest tooling residue.

## review

- Review the type as well as the term: before approving a reshape of
  standing machinery, ask what the subsystem did before the state being
  patched - main may be the regression, and a sane design stated directly
  beats archaeology.
- "I cannot understand this" is a complete verdict - delivered fast, burden
  on the artifact, diagnosis optional. Never treat the reviewer's
  incomprehension as the reviewer's failure.
- Test the plausible sentences a newcomer would derive from the names alone;
  a false one indicts the vocabulary, not the sentence.
- Deferred review points are the reviewer's to file - one should per issue,
  wired, linked from the PR - never prose the user must remember and relay.
- Before any act on a PR - closing, reviewing, commissioning - read its
  thread fresh: a standing review from another room is answered before new
  work is taken.
- Division of labor: Sonnet drafts PRs and code; Fable and the user
  review. The inverse mode is also rated: when the user authors, the
  assistant probes, verifies, and articulates - it does not rewrite.
- Findings are reported in chat BEFORE anything is posted to the forge -
  framing, severity, and blocker-or-issue are the maintainer's calls, and a
  posted comment is already spent. One approval covers one post.
  Verification runs (worktrees, gates, transcripts) are reads and need no
  permission.
- A fracture is an unavoidable consequence, stated with its remedy. A
  hazard the code could avoid is removed, never documented - a sentence
  asking anyone to remember, avoid, or be careful marks code that should
  simply not do the dangerous thing.

## issues and PRs

- An issue's record is body PLUS comments: `gh issue view <n> --json
  body,comments` before building it.
- blocked_by is the one issue relation - sub-issue/parent was retired
  2026-08-07; never use the sub_issues API. Wire it via
  `gh api -X POST repos/<o>/<r>/issues/<n>/dependencies/blocked_by
  -F issue_id=<id>`, never merely narrate it in prose ("part of #N" and its
  kin are refer-only vocabulary, per the issue template). Supersession
  transfers the old issue's relations.
- A PR body phrases completion "aims to complete #N" until the flip. The
  flip, on the reviewer's word only, is `yoga forge flip <pr>` - it arms
  the body's phrasing to `closes` and rewrites nothing. Commits are never
  rewritten (no squash, no reword - the branch merges as reviewed) and
  never carry the parser's words; the branch needs only to stand rebased
  on current origin/main AT MERGE, and the command relocates a moved base
  first - the lifetime's one rebase - and resyncs a clean checkout that
  holds the branch, announced. Its declaration
  (src/main/cli/forge/flip.json) is the authority for its steps. Never
  rebase eagerly: no open branch can know which merge comes next, so
  alignment is only information at the flip - eager alignment is work
  invalidated by every merge it did not predict. The forge's declared squash settings
  (squash_merge_commit_title: PR_TITLE and squash_merge_commit_message:
  COMMIT_MESSAGES, rows of src/main/cli/forge/forge.csv, explained in
  CONTRIBUTING.md, reconciled by `yoga forge`) publish the title as main's
  subject line and every commit's message and Signature as its body. A
  pre-merge rewrite destroys the review record and its corpus join keys.
- Keep the PR title as main's subject line: final indicative, describing
  what the branch became, current as the branch moves (#300's should,
  adopted as practice).
- A stacked PR follows exactly the ordinary workflow: when its parent
  squash-merges, `git rebase --onto origin/main <parent's old tip>` replays
  the branch's OWN commits onto the new main. Nothing is squashed - the
  single-commit shape some successors end with is an artifact of their
  content, never a requirement.
- A multi-commit branch is treated identically to a single-commit one at
  every step - review, rebase, flip, merge. No operation in the workflow
  distinguishes by commit count, and none may collapse one into the other.
- A merge verdict is a function of (base sha, head sha): keep the branch
  rebased onto current origin/main and ignore GitHub's `mergeable` flag -
  it is an unanchored cache.
- When origin/main has moved since the branch's base: rebuild by
  cherry-pick onto origin/main. Never `reset --soft origin/main` from a
  stale base - it keeps the old index and silently reverts every merge in
  between (the gate's check count betrays it).
- Any force-push rewrites the branch under a checkout that holds it:
  always resync the user's checkout yourself as the same act's last step -
  state what changed against what they held (a flip: the identical tree;
  a rebase: the new base and settled artifacts), run `git fetch origin &&
  git reset --hard origin/<branch>` there, and say so. If their tree is
  dirty, stop and report - never reset.
- Branches carry honest fix-up commits; never amend during review - the
  squash at merge produces the clean commit, and amending erases the record
  of what review changed.
- Keep linear history: a branch that needs main is rebased onto it, never
  merged into. After any rewrite, verify the replayed tree is identical
  (`git diff <old-tip> HEAD --stat` empty) and force-push with
  `--force-with-lease` against a sha read from `git ls-remote`, never one
  typed from memory. Hooks do not run at `rebase --continue` - a
  conflicted rebase can commit conflict markers unvetted; inspect before
  continuing. Never force-push any refspec containing main; before an amend
  or force-push, assert the branch as a hard gate
  (`[[ "$(git branch --show-current)" == "<branch>" ]]`), never as a
  printed check the chain ignores.
- The Signature grammar and its hooks are CONTRIBUTING.md's subject;
  bodies carry the triad by hand from machine-name.txt - never copy
  another room's.

## building

- Build in a worktree outside the user's checkout, created DETACHED:
  `git worktree add --detach <scratch>/wt-<issue> origin/main`. Never `-b` -
  a minted local branch inherits upstream origin/main and pollutes the
  user's later switch. Dispose of the worktree when its PR merges.
- Commit the WHOLE worktree state (`git add -A`); never curate the index -
  a partially staged commit publishes a tree the gate never arbitrated.
  Commit-gate-commit until clean: add, commit, add, commit - let the try
  fail.
- Push as `git push origin HEAD:refs/heads/issue-<n>-<slug>`.
- Never pipe a gating command (`git commit ... | tail -1` reports the
  pipe's tail, not the veto) - run it bare and let its failure stop the
  chain.
- Never chain `--amend` after a fallible step: an amend aims at whatever
  HEAD is, and a silently failed predecessor re-aims it at the wrong
  commit. Where a specific commit is meant, create it by construction
  (`git cherry-pick -n <sha> && git commit -m "<message>"`) rather than
  amending it into being.
- A demonstration of uncommitted work runs in the worktree, never against
  the branch ref - the ref lacks the edits, and the demo silently exercises
  old code.
- In the user's checkout: no commits, no pushes, no mutations, unbidden -
  and never ask to commit; the user announces satisfaction. Enacting verbs
  (sync, install, rm, deposits) run only when the current message asks;
  testing means the status and dry-run faces.
- If the repo is not greppable enough, fix the repo. A rename fixes every
  caller, printed remedies included.
- A file lives at the level of its subject and is named for its operation,
  never its caller, occasion, or reader. Names are singular, containers
  included. Identifiers name their referent - no contractions (s, V, errs),
  in probes as much as in committed code.
- Names specify and unify: roots classify by purpose, never by file format
  or language - content type is dressing, and polyglot faces of one
  operation are siblings by stem.
- Sibling files share one shape: field order and encoding match the family.
  When editing files programmatically, match each file's existing encoding;
  never re-encode strings the change does not touch.
- Comments state constraints an otherwise-correct edit would violate -
  nothing else. No narration, no provenance, no dates, no history; the
  retirement gradient is plainer name, smaller structure, declaration,
  generated code. History lives in commit messages and changelogs.
- Declarations: `r` and `w` hold repo-relative file path prefixes only;
  anything reaching outside the tree is a send or x by definition. What is
  intent, how is extent: prose says what a verb is FOR; its effects render
  from the declaration and are never restated by hand.
- Every script declares SELF as its repo-relative address and derives its
  root by searching parents for it - the gate holds every declaration.
- Scripted text edits use python string replacement, never sed or perl -
  path-laden patterns collide with delimiters.

## testing

- The user tests PRE-merge from the branch checkout, usr gate included, and
  merges from that checkout after the flip. Usr testing catches dev failure;
  the PR's "to test" prescribes that run and names its arbiter.
- Ordering and invalidation never derive from clocks: content and issued
  intents order; a timestamp is a label. CALCULUS L9 (Currency) is the
  system-side law.

## text and output

- Punctuation in everything repo-bound is " - " (space, hyphen, space).
  Both em-dash forms are wrong.
- The Signature is the only attribution: no generated-with footers, no
  co-author lines, anywhere.
- Write plainly: state the one fact, shortest path. Delete documentation
  that restates behavior rather than polishing it. Communication is for the
  other person - name branches, rooms, agents, and dates; no deixis, no
  knowledge that lives only in the writer's session.
- No arrow chains (a -> b -> c) in prose or replies - name the relation in
  words.
- No metonymy in output: printed relations name both sides concretely
  (local / remote-by-name); no repo imagery in code, output, commits, or
  replies.
- Moods are load-bearing: indicative only for facts anchored to a sha or
  date; "should" for every normative clause, titles included.
- Committed artifacts carry no indexicals: name the room and the date -
  "this machine" dereferences differently per room.
- Every time-word derives from a dereference performed this turn or is not
  written.
- Verify world state before asserting: re-check cheap external facts (git,
  files, push state) rather than restating transcript memory; an anchored
  claim needs no re-check - the anchor is the scoping.
- Command output keeps the contract: one ask, one verdict (done or not
  done), evidence beneath as grist. A verb wrapping an external authority
  echoes the command, executes it, and relays its verdict verbatim - never
  simulates the authority's judgment.
- Every artifact serves both audiences - human-amenable and agent-amenable,
  dual forms derived from one authority.
- When corrected, the artifact carries the fact only - no defense of the
  superseded framing.
- Mechanisms keep their tenses: an exception is the immanent present; a
  notification is a certified past (carrying its get) or an intensive
  future. Storing an exception converts it, and the tense must change with
  it.
