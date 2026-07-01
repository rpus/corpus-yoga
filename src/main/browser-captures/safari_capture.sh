#!/usr/bin/env bash
# Capture Claude.ai or Gemini conversations via Safari automation.
#
# Two modes:
#   (no args)     Navigate to site and capture all conversations.
#   --id <id>     Capture a single conversation (called by the macOS Shortcut).
#
# Usage:
#   src/main/browser-captures/safari_capture.sh --agent claude
#   src/main/browser-captures/safari_capture.sh --agent claude --id <uuid>
#   src/main/browser-captures/safari_capture.sh --agent gemini
#   src/main/browser-captures/safari_capture.sh --agent gemini --id <id>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

main() {
  local agent=""
  case "${1-}" in
    --agent) agent="$2"; shift 2 ;;
    --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
    *) echo "Usage: $0 --agent claude|gemini [--id <id>]" >&2; exit 1 ;;
  esac
  if [[ "$agent" != "claude" && "$agent" != "gemini" ]]; then
    echo "Usage: $0 --agent claude|gemini [--id <id>]" >&2; exit 1
  fi
  echo "src/main/browser-captures/$(basename "$0") ($agent)"
  local log
  log="$REPO_DIR/logs/src/main/browser-captures/safari_capture/$agent/$(date -u '+%Y-%m-%dT%H:%M:%SZ').log"
  mkdir -p "$(dirname "$log")"
  caffeinate -dim "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/safari_capture.py" --agent "$agent" "$@" \
    2>&1 | tee "$log"
}

main "$@"
