#!/usr/bin/env bash
# Convert a JSON Lines file to a JSON array and create a human-readable symlink.
#
# Usage:
#   src/main/code-agents/jsonl_to_json.sh <input.jsonl> <output.json>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

parse_args() {
  if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    grep "^# " "$0" | sed "s/^# //"; exit 0
  fi
  if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <input.jsonl> <output.json>"
    echo "Pass --help for more information."
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  local jsonl="$1" json_out="$2"

  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/jsonl_to_json.py" "$jsonl" "$json_out"

  local title_file="$json_out.title"
  if [[ -f "$title_file" ]]; then
    local raw_title; raw_title="$(cat "$title_file")"
    if [[ -n "$raw_title" ]]; then
      local slug; slug="$(echo "$raw_title" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/-*$//')"
      ln -sfn "$(basename "$json_out")" "$(dirname "$json_out")/${slug}.json"
    fi
  fi
}

main "$@"
