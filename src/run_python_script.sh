#!/usr/bin/env bash
# Run a Python script in the project venv.
#
# Usage:
#   src/run_python_script.sh <script.py> [args...]

set -euo pipefail

: "${VENV:=$HOME/venvs/general}"

parse_args() {
  case "${1:-}" in
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"

  if [[ ! -f "$VENV/bin/python" ]]; then
    echo "error: venv not found at $VENV — src/main/cli/pipeline/pipeline.sh creates it (override location via VENV=...)" >&2
    exit 1
  fi
  "$VENV/bin/python" "$@"
}

main "$@"
