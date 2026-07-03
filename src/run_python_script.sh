#!/usr/bin/env bash
# Run a Python script in the project venv.
#
# Usage:
#   src/run_python_script.sh <script.py> [args...]

set -euo pipefail

: "${VENV:=$HOME/venvs/general}"

parse_args() {
  case "${1:-}" in
    --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"

  if [[ ! -f "$VENV/bin/python" ]]; then
    echo "error: venv not found at $VENV — ./RUNME.sh creates it (override location via VENV=...)" >&2
    exit 1
  fi
  "$VENV/bin/python" "$@"
}

main "$@"
