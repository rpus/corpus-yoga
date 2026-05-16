#!/usr/bin/env bash
# Run a Python script in the project venv.
#
# Usage:
#   src/run_python_script.sh <script.py> [args...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //"
  exit 0
fi

main() {
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/activate_venv.sh"
  python "$@"
}

main "$@"
