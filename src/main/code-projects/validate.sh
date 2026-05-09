#!/usr/bin/env bash
# Convert and validate all .jsonl sessions in one Claude Code project directory.
#
# Usage:
#   src/main/code-projects/validate.sh --code-project <path/to/project-directory>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMA="$REPO_DIR/rsc/schema/code-projects/session/v1.json"
OUTPUT_DIR="$REPO_DIR/gen/code-projects"
JSONL_TO_JSON="$SCRIPT_DIR/jsonl_to_json.sh"

validate_session() {
  local jsonl="$1" project_name="$2"
  local session; session="$(basename "${jsonl%.jsonl}")"
  local out_dir="$OUTPUT_DIR/$project_name/$session"
  local json_out="$out_dir/session.json"
  local log_out="$out_dir/validation/session/v1.log"
  mkdir -p "$out_dir" "$(dirname "$log_out")"

  "$JSONL_TO_JSON" "$jsonl" "$json_out"

  {
    date -Iseconds
    echo "$jsonl: $(wc -l < "$jsonl" | xargs) lines, $(wc -c < "$jsonl" | xargs) bytes"
    echo "$SCHEMA: $(wc -c < "$SCHEMA" | xargs) bytes"
    python "$REPO_DIR/src/main/validate.py" "$json_out" "$SCHEMA"
  } > "$log_out"

  local status; status="$(grep -E '^Valid!|^Validation error' "$log_out" | head -1)"
  echo "  $session: $status"
}

validate_project() {
  local project_dir="${1%/}"
  local project_name; project_name="$(basename "$project_dir")"

  local found=0
  for jsonl in "$project_dir"/*.jsonl; do
    [ -f "$jsonl" ] || continue
    found=1
    validate_session "$jsonl" "$project_name"
  done

  if [[ "$found" -eq 0 ]]; then
    echo "  (no .jsonl files found)"
  fi
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //"
  exit 0
fi

main() {
  local code_project=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --code-project) code_project="$2"; shift 2 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --code-project <path>"
        echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$code_project" ]]; then
    echo "Usage: $0 --code-project <path/to/project-directory>"
    echo "       Pass --help for more information."
    exit 1
  fi

  # shellcheck source=/dev/null
  source "$REPO_DIR/src/activate_venv.sh"

  validate_project "$(cd "$code_project" && pwd)"
}

main "$@"
