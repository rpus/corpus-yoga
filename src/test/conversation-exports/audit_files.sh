#!/usr/bin/env bash
# Run the full file audit: build the normalised CSV and joined table
# (audit_files.py), then run all SQL queries against them (query_files.py).
#
# Usage:
#   src/test/conversation-exports/audit_files.sh --conversation-export  <path-to-export>
#   src/test/conversation-exports/audit_files.sh --conversation-exports <path-to-exports>
#
# Output: gen/<export>/audit_queries/

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 --conversation-export <path> | --conversation-exports <path>"
  echo "       Pass --help for more information."
  exit 1
fi

"$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_files.py" "$@"
"$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/query_files.py" "$@"
