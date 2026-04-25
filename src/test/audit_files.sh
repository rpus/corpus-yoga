#!/usr/bin/env bash
# Run the full file audit: build the normalised CSV and joined table
# (audit_files.py), then run all SQL queries against them (query_files.py).
#
# Usage:
#   src/test/audit_files.sh --data-dir  <path-to-export>
#   src/test/audit_files.sh --data-root <path-to-exports>
#
# Output: gen/<export>/audit_queries/

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 --data-dir <path> | --data-root <path>"
  echo "       Pass --help for more information."
  exit 1
fi

# shellcheck source=/dev/null
source ~/venvs/general/bin/activate
python "$SCRIPT_DIR/audit_files.py" "$@"
python "$SCRIPT_DIR/query_files.py" "$@"
deactivate
