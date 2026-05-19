#!/usr/bin/env bash
# Re-capture all conversations in ext/browser-captures/ as markdown and live API JSON.
# Requires Safari open, focused, and logged into claude.ai throughout.
#
# Usage:
#   src/main/browser-captures/safari_capture.sh --browser-captures ext/browser-captures

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) break ;;
    esac
  done
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/../../activate_venv.sh"
  caffeinate -dim python "$SCRIPT_DIR/safari_capture.py" "$@"
}

main "$@"
