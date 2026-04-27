#!/usr/bin/env bash
# Process Claude Code CLI session transcripts from ../code-sessions/.
#
# For each .jsonl file found:
#   1. Convert to a JSON array (one line → one element) using jsonl_to_json.py
#   2. Validate the array against rsc/schema/claude-code-sessions/v1.json
#   3. Write the converted JSON and validation log to gen/code-sessions/
#
# Usage:
#   ./RUNME-code-sessions.sh                               # all projects in ../code-sessions/
#   ./RUNME-code-sessions.sh --project claude-export-yoga  # one named project
#   ./RUNME-code-sessions.sh --sessions-root /other/path   # alternate root

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSIONS_ROOT="$(cd "$SCRIPT_DIR/../code-sessions" 2>/dev/null && pwd)" || {
  echo "Error: ../code-sessions/ not found. See doc/code-sessions-research.md for setup."
  exit 1
}
OUTPUT_DIR="$SCRIPT_DIR/gen/code-sessions"
SCHEMA="$SCRIPT_DIR/rsc/schema/claude-code-sessions/v1.json"
JSONL_TO_JSON="$SCRIPT_DIR/src/main/jsonl_to_json.py"
VALIDATE="$SCRIPT_DIR/src/main/validate.py"

run_session() {
  local jsonl="$1" project_name="$2"
  local session
  session="$(basename "${jsonl%.jsonl}")"
  local out_dir="$OUTPUT_DIR/$project_name/$session"
  mkdir -p "$out_dir"

  local json_out="$out_dir/session.json"
  local log_out="$out_dir/validation/claude-code-sessions/v1.log"
  mkdir -p "$(dirname "$log_out")"

  python "$JSONL_TO_JSON" "$jsonl" "$json_out"

  {
    date -Iseconds
    echo "$jsonl: $(wc -l < "$jsonl" | xargs) lines, $(wc -c < "$jsonl" | xargs) bytes"
    echo "$json_out: $(wc -c < "$json_out" | xargs) bytes"
    echo "$SCHEMA: $(wc -c < "$SCHEMA" | xargs) bytes"
    python "$VALIDATE" "$json_out" "$SCHEMA"
  } > "$log_out"

  local status
  status="$(grep -E '^Valid!|^Validation error' "$log_out" | head -1)"
  echo "  $session: $status"
}

run_project() {
  local project_dir="${1%/}"
  local project_name
  project_name="$(basename "$project_dir")"
  echo "$project_name"

  local found=0
  for jsonl in "$project_dir"/*.jsonl; do
    [ -f "$jsonl" ] || continue
    found=1
    run_session "$jsonl" "$project_name"
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
  local project="" sessions_root="$SESSIONS_ROOT"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --project)       project="$2";        shift 2 ;;
      --sessions-root) sessions_root="$2";  shift 2 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 [--project <name>] [--sessions-root <path>]"
        exit 1 ;;
    esac
  done

  # shellcheck source=/dev/null
  source ~/venvs/general/bin/activate

  if [[ -n "$project" ]]; then
    run_project "$sessions_root/$project"
  else
    for d in "$sessions_root"/*/; do
      [ -d "$d" ] || continue
      run_project "$d"
    done
  fi

  deactivate
}

main "$@"
