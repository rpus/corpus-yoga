#!/usr/bin/env bash
# prepare_commit_msg.sh — the prepare-commit-msg hook: stamp each commit with its
# drafting SIGNATURE, and strip the volatile model co-author. Grammar: rsc/COMMITS.md.
#
#   Signature: <machine>/<provider>/<session>      (a Claude Code session drafted it)
#   Signature: <machine>                           (no agent session in the environment)
#
# machine  — this machine's binding (rsc/machines/, its self-name), read at commit
#            time. The concrete axis, not the "room" metonym.
# provider — the AI provider that drafted it (claude, …), from AI_AGENT — the outer
#            corpus identity coordinate, so a signature reads like a corpus path.
# session  — the agent session id (uuid8) that drafted it, from CLAUDE_CODE_SESSION_ID.
#            It is the JOIN KEY into the captured session corpus
#            (input/<provider>/code/machine-transport/); the MODEL that did the work
#            is DERIVABLE from it (yoga agent models), accurately and plurally — so it
#            is never asserted here. This retired `Co-Authored-By: <model>`.
#
# Squash aggregates the per-commit signatures, so a landed idea drafted across
# machines/providers/sessions carries one line each — the honest multi-contributor
# record a single co-author could not give. The git AUTHOR stays the human: they own
# what lands; the signature records who DRAFTED it.
#
# Best-effort by design: any failure exits 0 so a signature never blocks a commit.

msg_file="${1:-}"; source_type="${2:-}"
[[ -n "$msg_file" && -f "$msg_file" ]] || exit 0
# merges and squashes assemble their own message; do not stamp them
case "$source_type" in merge|squash) exit 0 ;; esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || exit 0
repo="$(cd "$script_dir/../.." 2>/dev/null && pwd)" || exit 0

# The machine binding is machine-local and uncommitted; its joined path literal must
# not appear in committed text (it would strand xref — the very law the signature
# records). Build the path in pieces, as PREREQUISITES' check_room does.
binding="$repo/rsc/machines"; binding+="/self.txt"
machine='unbound'; [[ -f "$binding" ]] && machine="$(cat "$binding" 2>/dev/null || echo unbound)"
# A hook that rewrites commit messages must trust no input it didn't spell: a stray
# newline/space/slash in the binding would corrupt the trailer (a multiline value
# breaks out of it entirely). Hold it to the charset agent.py holds room labels to.
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
