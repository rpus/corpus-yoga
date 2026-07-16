# Commit trailers

Every commit carries a **`Signature:`** trailer per drafting agent-run:

    Signature: <machine>/<provider>/<session>      # a Claude Code session drafted it
    Signature: <machine>                           # no agent session in the environment

- **machine** — this machine's binding (`rsc/machines/`, its self-name), read at
  commit time. The concrete axis, not the "room" metonym. Always knowable.
- **provider** — the AI provider that drafted it (`claude`, …). The outer corpus
  identity coordinate, so a signature reads like the head of a corpus path.
- **session** — the agent session id (uuid8) that drafted it.

The hook attests **only what the environment positively provides**: the machine
always, the provider and session only when a Claude Code session is actually
present. When it is not, the signature stops at the machine and claims **nothing
about the drafter**. Absence of a session is *not* evidence of a human — a
different tool, a bot, a script, or a scrubbed environment all read the same. (A
`.../human` label would be the model-co-author's error in a new suit: asserting
the underivable from a missing signal.)

The **session is the join key** into the captured session corpus
(`input/<provider>/code/machine-transport/`). Crucially, the **model is not
recorded** — it is *derivable* from the session (`yoga agent models` counts
assistant records by model), accurately and plurally. This retired the
`Co-Authored-By: <model>` line, which was volatile, often false (the stamped
model rarely matched every record), and redundant with the session. Declarative
in data, derived not restated — the same law as `cache_io.path_for`.

A landed idea drafted across machines, providers, or sessions carries **one line
each** — squash aggregates the per-commit signatures. A single co-author line
cannot say "two agents, on two machines, shaped this"; the signature block does
(e.g. a squash spanning both rooms carries a signature from each).

The git **author stays the human** (git config). They own what lands; the
signature records who *drafted* it, not who *owns* it — the same split as
"curation is capture by a user".

Cherry-pick and rebase re-run this hook (source `commit`), so the *re-drafter's*
signature accumulates on a replayed commit beside the original's — a two-signature
commit reads as "first drafted here, replayed there," which is honest (they did
redraft it). `addIfDifferent` admits the distinct line without duplicating an
identical one; under squash-only this is nearly moot, but the reader deserves the
explanation.

Stamped by `src/test/prepare_commit_msg.sh` (the `prepare-commit-msg` hook, a
sibling of `src/test/pre_commit.sh`). Install (a convention, not a gate — so
optional, unlike the pre-commit hook):

    ln -sfn ../../src/test/prepare_commit_msg.sh .git/hooks/prepare-commit-msg

Install state is reported by `./PREREQUISITES.sh` and `./yoga machine`.
Best-effort: a signature failure never blocks a commit.
