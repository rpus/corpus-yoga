#!/usr/bin/env bash
# Run the repo-wide cross-reference audit.
# Output: src/test/xref.csv
#
# Usage:
#   src/test/xref.sh
#   src/test/xref.sh --out <path>    # override output path (default: src/test/xref.csv)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

parse_args() {
  case "${1:-}" in
    --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  "$SCRIPT_DIR/../run_python_script.sh" "$SCRIPT_DIR/xref.py" "$@"
}

main "$@"
