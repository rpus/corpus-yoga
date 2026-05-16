#!/usr/bin/env bash
# Generate per-schema definition catalogues as candidates for rsc/schema/model.json.
#
# Usage:
#   src/main/model/gen_model.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //"
  exit 0
fi

main() {
  "$SCRIPT_DIR/../../run_python_script.sh" "$SCRIPT_DIR/gen_model.py"
}

main "$@"
