<!-- How this file reaches you: `corpus-yoga forge raise issue --title <should>
     --body <file> [--blocked-by N]... [--blocks N]... [--supersedes N]` raises the
     issue (issues/887). The body FILE you draft holds the sections below from
     "## currently" on, without "### as at": the forge stamps the Signature from the
     triad the commit hook uses, derives the as-at anchor from the forge's main, and
     wires each relation given as an argument through the blocked_by API, posting a
     superseded issue's ledger note itself. The web form still serves this file as
     the prototype, but a body that carries a Signature line, an as-at, a harness
     footer, or a relation in prose - blocked by, blocks, part of, supersedes,
     closes, sub-issue - is refused by the raise: the argument wires what the phrase
     only narrated. The Signature is the body's ONE attribution; a harness default
     that appends its own has no licensed position in a body, exactly as
     prepare_commit_msg.sh's stamp already rules for commits.

     The grammar: an issue is a SHOULD. The title states it in one sentence,
     in should-form — the word appears — the property that should hold, never
     the instrument that should exist. An indicative title reads as a claim
     about the world and asserts nothing the body can close on: issues/429–issues/432
     ("the retirement completes"), each retitled by hand, are the worked
     example.
     The body separates what IS from what SHOULD BE, and the separation is
     carried by mood: every sentence under "currently" is indicative,
     checkable against the anchor, and immutable once anchored — a later
     state supersedes it under a new anchor, it never falsifies it; every
     sentence under "but, in future" is normative. A wish written as a fact,
     or a fact written as a wish, is manifestly ambiguous — it asserts
     nothing — and review should reject it like any other defect. The worked
     example: issues/259.

     Relations are the raise's arguments, wired as data: --blocked-by, --blocks
     (the parent of a part), --supersedes. In prose, "guards #N" refers to the
     check that holds an issue; "part of #N" and "supersedes #N" are refused, since
     the argument wires them, and `closes` is the PR grammar's one enacting word
     (.github/PULL_REQUEST_TEMPLATE.md) with no licensed position here.

     Closure: a PR that closes this issue should read as asserted compliance
     with "but, in future"; a standing property should end as a named check
     citing this issue; and the issue should close only on demonstration that
     its should holds — never on the existence of an instrument named for
     it. -->

Signature: <machine>/<provider>/<session>

## currently

### as at

<!-- DEFINES "currently": the branch and commit this issue observes, plus the
     causal PR where one merge produced the state. Without this anchor,
     "currently" dereferences differently for every reader and every week;
     with it, every sentence in "as is" is a checkable, immutable claim. -->

main @ <sha>[, after #<N> merged]

### as is

<!-- The state at issue: indicative only, every claim readable against the
     anchor above — file:line quotes, observed output, measured numbers (a
     machine-local measurement additionally names its room). What is wrong
     appears here only as observed fact; why it is wrong is the contrast the
     next section draws. -->

## but, in future

<!-- The to-be: normative throughout, "should" in every clause. Contrast and
     improve the as-is; state the property that should hold, never the
     mechanism that should exist. This section is what a closing PR asserts
     compliance with, and what its standing check cites. -->
