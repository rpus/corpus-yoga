#!/usr/bin/env bash
# Run a Python script in the project venv, its imports found under the roots pyrightconfig.json
# declares - the one list the editor, the type checker and the running code read (issues/1038).
#
# Usage:
#   src/run_python_script.sh <script.py> [args...]

set -euo pipefail
REPO_DIR="${CORPUS_YOGA_ROOT:?the repository root, which corpus-yoga hands every run it starts}"
# shellcheck source=src/import_roots.sh
source "$REPO_DIR/src/import_roots.sh"

: "${CORPUS_YOGA_VENV:=$HOME/venvs/general}"

parse_args() {
  case "${1:-}" in
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"

  if [[ ! -f "$CORPUS_YOGA_VENV/bin/python" ]]; then
    echo "error: venv not found at $CORPUS_YOGA_VENV - the mint is corpus-yoga status satisfy, pre-venv ./corpus-yoga status satisfy (override location via CORPUS_YOGA_VENV=...)" >&2
    exit 1
  fi
  import_roots "$REPO_DIR" "$CORPUS_YOGA_VENV/bin/python"
  "$CORPUS_YOGA_VENV/bin/python" "$@"
}

main "$@"
