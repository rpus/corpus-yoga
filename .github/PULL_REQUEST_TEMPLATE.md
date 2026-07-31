<!-- How this file reaches you: the web form serves it into a new PR's description
     box; `gh pr create` reads it only via --template .github/PULL_REQUEST_TEMPLATE.md;
     with --body-file (both rooms' practice) it is the PROTOTYPE you copy from.

     The grammar (#124): why / what / how / to. The durable half belongs on the
     branch's FIRST commit — prospective at branch birth ("this branch should…"),
     flipped to final indicative form before merge — because the squash publishes
     commit messages, oldest first, and nothing else survives into git history.
     This body teaches the same sections plus the review-facing half.

     Relations vocabulary: enacts / advances / supersedes / reopens / leaves open.
     NEVER a closing keyword beside an issue number, even quoted or negated — the
     forge's parser reads free prose (writing "does NOT close #N" once closed #N). -->

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
     they believe they built; the defects live outside that belief. -->

- **test** — <how a reviewer reproduces the verdicts: commands run, outputs seen>
- **use** — <what a machine runs or expects after merge — spoken in yoga commands;
  forge merge ends by running `yoga prerequisites`, so machine-local adoption belongs
  in its report: state it cannot see is a species to add (the mount precedent), not
  prose to remember>
- **do** — <what this raises, advances, or leaves open, with its issue>
