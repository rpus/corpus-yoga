# shellcheck shell=bash
# enact.sh — the shell face of the echo-execute-trap-relay primitive (sourced, not executed).
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
# evidence, and the consuming verb's closing envelope is the one done-line.
#
# query() is the read face: the answer is captured for the caller AND relayed to the
# narrative (`= <answer>`), so a transcript never shows an unresolved echo.
#
# CONSTRAINT ON EVERY CALLER, unenforceable here: the narrative rides stderr. A call
# site that redirects stderr away (2>/dev/null, 2>&1 >/dev/null) silences the echo and
# the failure relay — a wrapped act rendered invisible, the wrap decorative. Claim the
# wrapped command's own streams if unwanted; never the narrative's.

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
