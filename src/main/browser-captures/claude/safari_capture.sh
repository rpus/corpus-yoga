#!/usr/bin/env bash
# Capture Claude.ai conversations via Safari automation.
#
# Two modes:
#   (no args)     Navigate to claude.ai/recents and capture all conversations.
#   --uuid <uuid> Capture a single conversation (called by the macOS Shortcut).
#
# Usage:
#   src/main/browser-captures/claude/safari_capture.sh
#   src/main/browser-captures/claude/safari_capture.sh --uuid <uuid>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

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
  local log
  log="$REPO_DIR/logs/${SCRIPT_DIR#"$REPO_DIR/"}/safari_capture/$(date -u '+%Y-%m-%dT%H:%M:%SZ').log"
  mkdir -p "$(dirname "$log")"
  caffeinate -dim "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/safari_capture.py" "$@" \
    | tee "$log"
}

main "$@"
