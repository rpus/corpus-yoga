#!/usr/bin/env bash
# Run a Python script in the project venv, its imports found under the roots pyrightconfig.json
# declares - the one list the editor, the type checker and the running code read (issues/1038).
#
# Usage:
#   src/run_python_script.sh <script.py> [args...]

set -euo pipefail
SELF='src/run_python_script.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
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
    echo "error: venv not found at $CORPUS_YOGA_VENV - the mint is corpus-yoga status satisfy, pre-venv ./src/main/cli/status/status.sh satisfy (override location via CORPUS_YOGA_VENV=...)" >&2
    exit 1
  fi
  import_roots "$REPO_DIR" "$CORPUS_YOGA_VENV/bin/python"
  "$CORPUS_YOGA_VENV/bin/python" "$@"
}

main "$@"
