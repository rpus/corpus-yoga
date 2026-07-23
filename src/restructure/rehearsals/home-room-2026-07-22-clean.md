# Rehearsal record — home-room, 2026-07-22 (third measurement: the clean bar)

Follow-up to [home-room-2026-07-22.md](./home-room-2026-07-22.md), after two
things landed on both sides: PR #18 (indexing sync joins yoga run; the index
header stops naming a tier path) merged to main and into this branch
(caa180b), and a full `yoga run` on current main brought the real corpus
current — the recipe's new step 0, learned the hard way the same day.

## The verdict

Two full worktree passes (run now folds memories, summaries, supersede, and
the index itself), 0 FAIL, 0 WARN, then:

    markdown: 545 byte-identical, 0 differ, 0 missing, 0 extra
    artifacts: stable
    dashboard: stable
    indexing: stable
    memories: stable
    serve_markdown: stable

Zero residuals, zero explanations. The byte-identical bar — which never had
a coded exemption — is now simply met: the corpus does not notice the move.
The one artifact that structurally could not pass (index.md, whose header
embedded a tier path) passes since #18 removed the path from the header;
both sides regenerate it identically.

## The apply plan (dry run — NOT executed)

As found, the plan refused: `CONFLICT local: logs AND tmp/logs both exist`
(the gate-born tmp/, as the recipe's step 5 predicts). After the prescribed
`rm -rf tmp`, the clean plan:

    6 move(s) to perform: {'data': 3, 'mount': 1, 'local': 2}
      LINK ext/claude-code-projects -> /Users/khalidkhan/.claude/projects
      LINK data -> /Users/khalidkhan/Documents/dev/com/github/rpus/claude-export-yoga/data
      UNLINK input/claude, input/gemini, output (old moorings, subsumed by data/)
    dry run (pass --apply to perform)

Home-room's rehearsal obligations are complete: manifest totality OK, the
equivalence bar met with nothing to explain, the refusal path and its remedy
both exercised. Awaiting reading-room's record; whichever room applies first
performs the shared medium move, the second finds it done.

(The two absolute paths above are home-room's own moorings, quoted from its
dry run — they describe this room's disk on this date, no other.)
