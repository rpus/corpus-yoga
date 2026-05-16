#!/usr/bin/env bash
# Fetch the live API JSON for each conversation in a browser-captures batch.
# Requires Safari open and logged into claude.ai.
#
# Usage:
#   ./src/main/browser-captures/safari_fetch_api_json.sh --browser-capture ext/browser-captures/data-<...>
#   ./src/main/browser-captures/safari_fetch_api_json.sh --browser-captures ext/browser-captures

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
  caffeinate -dim python "$SCRIPT_DIR/safari_fetch_api_json.py" "$@"
}

main "$@"
