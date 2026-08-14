# shellcheck shell=bash
# enact.sh — the shell face of the echo-execute-trap-relay primitive (sourced by bash, not executed).
#
# The one function every external command should run through: echo it, execute it, trap its
# status, relay the verdict. Verbatim streams — the wrapped command's stdout and stderr
# flow to the caller's own, uncaptured. The narrative (the echo, the verdict) goes to
# stderr, so `out=$(enact cmd...)` captures exactly the command's own stdout.
#
# The seam for the enactment-guard tier (#256): the one place a future policy would gate,
# warn, or attribute an act, because every act already passes through here. Not implemented.
#
# The wrapper RETURNS the status; on failure the relay always prints, bare or
# `||`-tested alike, even under set -e — the caller's own errexit then applies AFTER
# the relay, by the caller's rules. Success is silent: an act's own output is its
# evidence, and what a verb says when it finishes is the verb's own business.
#
# query(), quote() and quiet() are the read faces, named for how many times each
# renders the answer: query twice (the `= <answer>` relay plus stdout, capture-and-
# chain); quote once (stdout only); quiet zero (echoes the command, discards the
# answer). Failure is never quiet in any of these faces. attempt() is the one
# exception, for the one caller-class that has DECLARED the nonzero status an
# expected state it handles (#485): it echoes and runs like enact but relays no
# verdict, and its caller MUST narrate the state in the mechanism's own voice -
# an attempt whose status vanishes unnarrated is the wrap rendered decorative. On failure query and quote return the
# status; the python face raises — the pair's one ruled asymmetry (#277); the relay
# words themselves are held identical by the gate.
#
# CONSTRAINT ON EVERY CALLER, unenforceable here: the narrative rides stderr. A call
# site that redirects stderr away (2>/dev/null, 2>&1 >/dev/null) silences the echo and
# the failure relay — a wrapped act rendered invisible, the wrap decorative.

enact() {
  local printed status
  printed="$(printf '%q ' "$@")"
  printed="${printed% }"
  echo "enact: $printed" >&2
  "$@" && status=0 || status=$?
  if [[ "$status" -ne 0 ]]; then
    echo "NOT done (exit $status): $printed" >&2
  fi
  return "$status"
}

attempt() {
  local printed status
  printed="$(printf '%q ' "$@")"
  printed="${printed% }"
  echo "attempt: $printed" >&2
  "$@" && status=0 || status=$?
  return "$status"
}

query() {
  local printed answer status
  printed="$(printf '%q ' "$@")"
  printed="${printed% }"
  echo "query: $printed" >&2
  answer="$("$@")" && status=0 || status=$?
  if [[ "$status" -eq 0 ]]; then
    echo "= $answer" >&2
    printf '%s\n' "$answer"
  else
    echo "NOT done (exit $status): $printed" >&2
  fi
  return "$status"
}

quote() {
  local printed answer status
  printed="$(printf '%q ' "$@")"
  printed="${printed% }"
  echo "quote: $printed" >&2
  answer="$("$@")" && status=0 || status=$?
  if [[ "$status" -eq 0 ]]; then
    printf '%s\n' "$answer"
  else
    echo "NOT done (exit $status): $printed" >&2
  fi
  return "$status"
}

quiet() {
  local printed status
  printed="$(printf '%q ' "$@")"
  printed="${printed% }"
  echo "quiet: $printed" >&2
  "$@" >/dev/null && status=0 || status=$?
  if [[ "$status" -ne 0 ]]; then
    echo "NOT done (exit $status): $printed" >&2
  fi
  return "$status"
}
