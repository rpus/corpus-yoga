#!/usr/bin/env bash
# Run a Python script in the project venv.
#
# Usage:
#   src/run_python_script.sh <script.py> [args...]

set -euo pipefail

: "${CORPUS_YOGA_VENV:=$HOME/venvs/general}"

parse_args() {
  case "${1:-}" in
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"

  if [[ ! -f "$CORPUS_YOGA_VENV/bin/python" ]]; then
    echo "error: venv not found at $CORPUS_YOGA_VENV - the mint is corpus-yoga status sync --apply, pre-venv ./src/main/cli/status/status.sh sync --apply (override location via CORPUS_YOGA_VENV=...)" >&2
    exit 1
  fi
  "$CORPUS_YOGA_VENV/bin/python" "$@"
}

main "$@"
