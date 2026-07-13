#!/usr/bin/env bash
# Run the full file audit: build the normalised CSV and joined table
# (audit_files.py), then run all SQL queries against them (query_files.py).
#
# Usage:
#   src/main/chat-exports/audit_files.sh --chat-export  <path-to-export>
#   src/main/chat-exports/audit_files.sh --chat-exports <path-to-exports>
#
# Output: cache/chat-exports/<export>/audit_queries/

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 --chat-export <path> | --chat-exports <path>"
  echo "       Pass --help for more information."
  exit 1
fi

"$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_files.py" "$@"
"$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/query_files.py" "$@"
