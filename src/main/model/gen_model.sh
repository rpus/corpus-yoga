#!/usr/bin/env bash
# Generate per-schema definition catalogues as candidates for rsc/schema/model.json.
#
# Usage:
#   src/main/model/gen_model.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

parse_args() {
  case "${1:-}" in
    --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  "$SCRIPT_DIR/../../run_python_script.sh" "$SCRIPT_DIR/gen_model.py"
}

main "$@"
