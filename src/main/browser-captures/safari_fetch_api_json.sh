#!/usr/bin/env bash
# Backfill live API JSON for shortcut-mode captures that have markdown but no JSON.
# Requires Safari open, focused, and logged into claude.ai throughout.
#
# Usage:
#   src/main/browser-captures/safari_fetch_api_json.sh --browser-captures ext/browser-captures

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

  caffeinate -dim "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/safari_fetch_api_json.py" "$@"
}

main "$@"
