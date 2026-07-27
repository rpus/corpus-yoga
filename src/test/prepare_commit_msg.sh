#!/usr/bin/env bash
# prepare_commit_msg.sh — the prepare-commit-msg hook: stamp each commit with its
# drafting SIGNATURE, and strip the volatile model co-author. This header is the
# grammar's ONE home — the hook implements it, so nothing restates it elsewhere.
#
#   Signature: <machine>/<provider>/<session>      (a Claude Code session drafted it)
#   Signature: <machine>                           (no agent session in the environment)
#
# machine  — this machine's binding (machine-name.txt, its self-name), read at
#            commit time. The concrete axis, not the "room" metonym. Always knowable.
# provider — the AI provider that drafted it (claude, …), from AI_AGENT — the outer
#            corpus identity coordinate, so a signature reads like a corpus path.
# session  — the agent session id (uuid8) that drafted it, from CLAUDE_CODE_SESSION_ID.
#            It is the JOIN KEY into the captured session corpus
#            (data/input/<provider>/code/machine-transport/); the MODEL that did the work
#            is DERIVABLE from it (yoga agent models), accurately and plurally — so it
#            is never asserted here. This retired `Co-Authored-By: <model>`.
#
# Attest ONLY what the environment positively provides: absence of a session is not
# evidence of a human (another tool, a bot, a scrubbed env all read the same), so the
# second form claims the machine and nothing whatever about the drafter.
#
# The git AUTHOR stays the human: they own what lands; the signature records who
# DRAFTED it — the same split as "curation is capture by a user" (rsc/CALCULUS.md).
#
# MULTIPLE SIGNATURES. git parses trailers only in a message's LAST paragraph, so:
#   - co-drafting ONE commit (a second agent amends/cherry-picks/rebases it; each hook
#     run adds its line to the same block) -> every signature is a parsed trailer;
#     addIfDifferent admits a distinct line, never a duplicate. This is the clean case.
#   - separate commits squashed -> the messages concatenate, so only the LAST signature
#     parses; earlier ones survive as body text. A fair hint the PR was not atomic.
# And none of it reaches main unless the forge composes the squash body from the commit
# messages: squash_merge_commit_message, declared in rsc/forge.csv and reconciled by
# ./src/prerequisites.sh. Under PR_BODY the message — trailers and all — is discarded whole.
#
# Install (a convention, not a gate, so optional unlike the pre-commit hook):
#   ln -sfn ../../src/test/prepare_commit_msg.sh .git/hooks/prepare-commit-msg
#
# Best-effort by design: any failure exits 0 so a signature never blocks a commit.

msg_file="${1:-}"; source_type="${2:-}"
[[ -n "$msg_file" && -f "$msg_file" ]] || exit 0
# merges and squashes assemble their own message; do not stamp them
case "$source_type" in merge|squash) exit 0 ;; esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || exit 0
repo="$(cd "$script_dir/../.." 2>/dev/null && pwd)" || exit 0

# The machine binding: machine-local, uncommitted, and rooted beside the other
# machine-local entries. Its own .gitignore rule is what lets this name it whole.
binding="$repo/machine-name.txt"
machine='unbound'; [[ -f "$binding" ]] && machine="$(cat "$binding" 2>/dev/null || echo unbound)"
# A hook that rewrites commit messages must trust no input it didn't spell: a stray
# newline/space/slash in the binding would corrupt the trailer (a multiline value
# breaks out of it entirely). Hold it to the charset agent.py holds machine labels to.
machine="$(tr -cd 'A-Za-z0-9_-' <<< "$machine")"; [[ -n "$machine" ]] || machine='unbound'

if [[ -n "${CLAUDE_CODE_SESSION_ID:-}" ]]; then
  provider="${AI_AGENT%%-*}"; [[ -n "$provider" ]] || provider='agent'
  signature="Signature: ${machine}/${provider}/${CLAUDE_CODE_SESSION_ID:0:8}"
else
  # No agent session in the environment. The machine is known; the drafter is NOT.
  # Assert only the machine — absence of a Claude Code session is NOT evidence of a
  # human (a different tool, a bot, a script, or a scrubbed env all read the same).
  # Inferring "human" from a missing var would be the model-co-author's error again:
  # asserting the underivable. Attest only what the environment positively provides.
  signature="Signature: ${machine}"
fi

# Strip the model co-author, anchored on the Anthropic bot email — the invariant
# part, stable across model renames, and the only thing that reliably marks a
# machine line. A human co-author stays, even one named Claude (Claudette,
# Claude Debussy). Then git places the signature in the trailer block;
# addIfDifferent keeps it idempotent across amend while still letting distinct
# signatures accumulate.
processed="$( { grep -viE '^Co-Authored-By: .*<noreply@anthropic\.com>' "$msg_file" 2>/dev/null || true; } \
  | git interpret-trailers --if-exists addIfDifferent --trailer "$signature" 2>/dev/null )" || exit 0
[[ -n "$processed" ]] && printf '%s\n' "$processed" > "$msg_file"
exit 0
