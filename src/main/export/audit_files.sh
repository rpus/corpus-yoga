#!/usr/bin/env bash
# Run the full file audit: build the normalised CSV and joined table
# (audit_files.py), then run all SQL queries against them (query_files.py).
#
# Usage:
#   src/main/export/audit_files.sh --export  <path-to-export>
#   src/main/export/audit_files.sh --exports <path-to-exports>
#
# Output: cache/pipeline/claude/chat/bulk-export/<export>/audit_queries/

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${CORPUS_YOGA_ROOT:?the repository root, which corpus-yoga hands every run it starts}"

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 --export <path> | --exports <path>"
  echo "       Pass --help for more information."
  exit 1
fi

"$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_files.py" "$@"
"$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/query_files.py" "$@"
