#!/usr/bin/env bash
# Convert a JSON Lines file to a JSON array.
#
# Usage:
#   src/main/code-projects/jsonl_to_json.sh <input.jsonl> <output.json>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //"
  exit 0
fi

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <input.jsonl> <output.json>"
  exit 1
fi

"$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/jsonl_to_json.py" "$1" "$2"
