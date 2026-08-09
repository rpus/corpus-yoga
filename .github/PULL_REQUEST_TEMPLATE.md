<!-- How this file reaches you: the web form serves it into a new PR's description
     box; `gh pr create` reads it only via --template .github/PULL_REQUEST_TEMPLATE.md;
     with --body-file (both rooms' practice) it is the PROTOTYPE you copy from.

     The body opens with a Signature line, the same triad the commit hook
     stamps (src/test/prepare_commit_msg.sh's header is the one authority for
     the grammar): `Signature: <machine>/<provider>/<session>`. Written by
     hand — no hook stamps a body — since raise time has no commit to hook.
     The Signature is the body's ONE attribution. A harness default that
     appends its own — a generated-with footer, a co-author line — has no
     licensed position in a body, exactly as prepare_commit_msg.sh's stamp
     already rules for commits; strip it before raising.

     The grammar (#124): why / what / how / to. The durable half belongs on the
     branch's FIRST commit — prospective at branch birth ("this branch should…"),
     flipped to final indicative form before merge — because the squash publishes
     commit messages, oldest first, and nothing else survives into git history.
     This body teaches the same sections plus the review-facing half.

     Relations vocabulary: closes / enacts / advances / supersedes / reopens.
     The protection is LEXICAL: every relation but one only REFERS —
     `#N` alone never enacts, whatever section it sits in. `closes #N` is the
     vocabulary's one ENACTING word, parser-aligned: the forge executes it at
     merge, atomically, wherever it appears (the parser is position-blind — the
     why-section lead is style, not safety). Never spell the parser's other words
     near an issue number, even quoted or negated: "does NOT close #N" once
     closed #N. An issue completed by a PR that does not say closes is residue.
     MENTIONS wear backticks: to speak ABOUT a marker phrase or keyword without
     using it, backtick it — checks strip backticked spans before matching, and
     backticks are the one safe mark (quotes mis-pair on apostrophes).
     MOOD LAW: closes is indicative-only. A branch-birth commit must not carry
     it — the promise would execute at merge regardless of what review decided
     in between. The BODY obeys the same law: the parser reads it at merge too,
     so a raised body's why and do sections phrase completion prospectively
     ("aims to complete #N") exactly as the commits do. The pre-merge flip is
     the ONE act that arms the close — recompose to the final commit AND edit
     the body's "aims to complete" to closes, together, on the reviewer's
     word — which makes the recompose load-bearing: if review narrowed the
     scope, withholding closes is not tidying prose, it is preventing a wrong
     close. -->

Signature: <machine>/<provider>/<session>

## why

- **#N** — <relation>: <the intent, in issue-graph terms — achievement-agnostic>

## what

- **fractures** — <a name or meaning the surface loses; who breaks>
  - None.
- **features** — <what the surface gains>
  - None.
- **fixes** — <what is repaired under an unchanged surface>
  - None.

<!-- All three lists stay present; "None." is a statement, not an omission.
     Name-first rendering: every item leads with the name it is about, nested by
     containment (command → verbs, file → findings); description after the dash. -->

## how

<!-- Authorial implementation notes: why THIS WAY — the approach chosen among
     alternatives, the mechanism, the invariant relied on. What the diff cannot
     show; never a narration of what it shows. The one home for the voice that
     code comments refuse. -->

## to

<!-- "to test" is the AUTHOR'S CLAIM — a starting point for a reviewer, never a
     substitute for one: reproduce these, then go looking. An author tests what
     they believe they built; the defects live outside that belief.

     The line OPENS by naming the arbiter: the dev gate (yoga test run), the usr
     gate (yoga pipeline run), both, or a named other (the editor; a live run).
     A change one gate cannot arbitrate carries a declared arbiter instead of a
     per-PR apology — the dev gate is green on both sides of a dead step import,
     and only the usr gate's red names it (#335 is the worked example).

     The declaration is CHECKABLE AGAINST THE DIFF: the changed paths derive a
     default arbiter (docs and .github — the reader; src/test/dev and schemas —
     the dev gate; pipeline and model code — the usr gate), so a reviewer holds
     the declared arbiter to the derived one. A declaration that DEVIATES from
     its path-default is not an error but the signal — #335's paths derived
     dev-gate while the true arbiter was the usr gate — the deviation record
     review leans into, diagnostic_skip's grammar. -->

- **test** — <arbiter: which gate(s) arbitrate this change — then how a reviewer
  reproduces the verdicts: commands run, outputs seen>
- **use** — <what a machine runs or expects after merge — spoken in yoga commands;
  machine-local adoption belongs in `yoga prerequisites`' report: state it cannot
  see is a species to add (the mount precedent), not prose to remember>
- **do** — <what this raises or advances, with its issue>
