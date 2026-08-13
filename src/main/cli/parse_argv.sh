# shellcheck shell=bash
# parse_argv.sh — the bash face of parse_argv.py (#474): sourced by a bash target,
# called at each verb's dispatch as `parse_argv <command> <verb> "$@"`. Answers
# -h/--help from the verb's declaration and refuses argv the declaration does not
# express; on validated argv it returns and the caller proceeds with "$@" unchanged.
# The python face is the one reader of src/main/cli/ — this file is a courier of
# its verdict and parses nothing itself.

# Sourced file: SELF and _self_dir here overwrite the sourcing script's — safe only
# because every sourcer's own guard has already run by its source line.
SELF='src/main/cli/parse_argv.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARSE_ARGV_REPO="${_self_dir%/"${SELF%/*}"}"
[[ "${PARSE_ARGV_REPO}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

parse_argv() {
  local out rc=0
  # `|| rc=$?` keeps a caller's set -e from killing the script at the substitution
  # itself. A refusal (rc 2) needs no relay: argparse wrote it to stderr, which
  # $(...) does not capture.
  out="$(python3 "$PARSE_ARGV_REPO/src/main/cli/parse_argv.py" "$@")" || rc=$?
  # $(...) ate the face's trailing newline; printf '%s\n' restores exactly one,
  # so the courier's bytes equal the face's (cli.verb_help_answered holds this).
  case "$rc" in
    0) [[ -z "$out" ]] || { printf '%s\n' "$out"; exit 0; } ;;
    *) exit "$rc" ;;
  esac
}
