# shellcheck shell=bash
# enact.sh — the shell face of the echo-execute-trap-relay primitive (sourced, not executed).
#
# The one function every external command runs through: echo it, execute it, trap its
# status, relay the verdict. Verbatim streams — the wrapped command's stdout and stderr
# flow to the caller's own, uncaptured. The narrative (the echo, the verdict) goes to
# stderr, so `out=$(enact cmd...)` captures exactly the command's own stdout.
#
# The seam for the enactment-guard tier (#256): the one place a future policy would gate,
# warn, or attribute an act, because every act already passes through here. Not implemented.
#
# The wrapper RETURNS the status; the relay always prints, bare or `||`-tested alike,
# even under set -e — the caller's own errexit then applies AFTER the relay, by the
# caller's rules.

enact() {
  local printed status
  printed="$(printf '%q ' "$@")"
  printed="${printed% }"
  echo "enact: $printed" >&2
  "$@" && status=0 || status=$?
  if [[ "$status" -eq 0 ]]; then
    echo "done: $printed" >&2
  else
    echo "NOT done (exit $status): $printed" >&2
  fi
  return "$status"
}
