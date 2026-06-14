#!/usr/bin/env bash
# Capture all conversations from claude.ai and gemini.google.com into ext/browser-captures/.
# Requires Safari open, focused, and logged into both sites throughout.
#
# Usage:
#   src/main/browser-captures/PREP.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

parse_args() {
  discover=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --discover) discover="1"; shift ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  mkdir -p "$REPO_DIR/ext/browser-captures/claude"
  mkdir -p "$REPO_DIR/ext/browser-captures/gemini"
  if [[ -n "$discover" ]]; then
    "$SCRIPT_DIR/claude/safari_capture.sh" --discover
    "$SCRIPT_DIR/gemini/safari_capture.sh" --discover
  else
    echo "skipping capture (--browser-captures not passed to RUNME.sh)"
  fi
}

main "$@"
