#!/usr/bin/env bash
# prepare_commit_msg.sh — the prepare-commit-msg hook: stamp each commit with its
# drafting SIGNATURE, and strip volatile model co-authors.
#
#   Signature: <machine>/<provider>/<session>      (an agent session drafted it)
#   Signature: <machine>                           (no agent session in the environment)
#
# machine  — this machine's binding (machine-name.txt, its self-name), read at
#            commit time. The concrete axis, not the "room" metonym. Always knowable.
# provider — the AI provider that drafted it (claude, gemini, …), from the provider registry
#            (rsc/provider/providers.csv), matching the outer corpus identity coordinate.
# session  — the agent session id (uuid8) that drafted it. It is the JOIN KEY into the
#            captured session corpus (data/input/<provider>/code/machine-transport/);
#            the MODEL that did the work is DERIVABLE from it, accurately and plurally.
#
# Attest ONLY what the environment positively provides: absence of a session is not
# evidence of a human (another tool, a bot, a scrubbed env all read the same), so the
# second form claims the machine and nothing whatever about the drafter.
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
machine="$(tr -cd 'A-Za-z0-9_-' <<< "$machine")"; [[ -n "$machine" ]] || machine='unbound'

# Derive signature and bot-author filter from the provider registry
signature="$(python3 -c "import sys; sys.path.insert(0, '$repo/src/main'); import provider; print(provider.active_signature('$machine'))" 2>/dev/null)" || signature="Signature: ${machine}"
bot_filter="$(python3 -c "import sys; sys.path.insert(0, '$repo/src/main'); import provider; print('|'.join(provider.bot_author_patterns()))" 2>/dev/null)" || bot_filter='.*<noreply@anthropic\.com>|.*<noreply@google\.com>'

# Strip declared model co-authors, then place the signature in the trailer block;
# addIfDifferent keeps it idempotent across amend while letting distinct signatures accumulate.
processed="$( { grep -viE "^Co-Authored-By: (${bot_filter})" "$msg_file" 2>/dev/null || true; } \
  | git interpret-trailers --if-exists addIfDifferent --trailer "$signature" 2>/dev/null )" || exit 0
[[ -n "$processed" ]] && printf '%s\n' "$processed" > "$msg_file"
exit 0
