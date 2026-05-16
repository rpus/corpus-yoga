#!/usr/bin/env bash
# Export every conversation in a bulk export to markdown via Safari automation.
# Requires Safari open, focused, and logged into claude.ai throughout.
#
# Usage:
#   ./src/main/browser-captures/safari_capture.sh --chat-export  ext/chat-exports/data-<...>
#   ./src/main/browser-captures/safari_capture.sh --chat-exports ext/chat-exports
# Output goes to ext/browser-captures/<export-name>/<uuid>/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //"
  exit 0
fi

main() {
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/../../activate_venv.sh"
  # caffeinate -dim: prevent display sleep (-d), idle sleep (-i), and disk sleep (-m)
  caffeinate -dim python "$SCRIPT_DIR/safari_capture.py" "$@"
}

main "$@"
