#!/usr/bin/env bash
# Seed ext/browser-captures/ by capturing all conversations in ext/chat-exports/.
# Requires Safari open, focused, and logged into claude.ai throughout.
#
# Usage:
#   src/main/browser-captures/PREP.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  "$SCRIPT_DIR/safari_capture.sh" --browser-captures "$REPO_DIR/ext/browser-captures"
}

main "$@"
