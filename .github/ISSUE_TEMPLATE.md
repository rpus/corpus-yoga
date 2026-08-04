<!-- How this file reaches you: the web form serves it into a new issue's
     description box from the default branch; `gh issue create` offers it
     interactively; with `--body-file` (both rooms' practice) it is the
     PROTOTYPE you copy from — a stale clone's copy lags the remote until
     pulled, and nothing checks that.

     The body opens with a Signature line, the same triad the commit hook
     stamps (rsc/test/prepare-commit-msg-hook.sh's header is the one authority for
     the grammar): `Signature: <machine>/<provider>/<session>`. Written by
     hand — no hook stamps a body — since raise time has no commit to hook.

     The grammar: an issue is a SHOULD. The title states it in one sentence —
     the property that should hold, never the instrument that should exist.
     The body separates what IS from what SHOULD BE, and the separation is
     carried by mood: every sentence under "currently" is indicative,
     checkable against the anchor, and immutable once anchored — a later
     state supersedes it under a new anchor, it never falsifies it; every
     sentence under "but, in future" is normative. A wish written as a fact,
     or a fact written as a wish, is manifestly ambiguous — it asserts
     nothing — and review should reject it like any other defect. The worked
     example: #259.

     Relations vocabulary, referring only: "part of #N", "supersedes #N",
     "guards #N". No word in an issue body enacts anything — `closes` is the
     PR grammar's one enacting word (.github/PULL_REQUEST_TEMPLATE.md) and
     has no licensed position here.

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
