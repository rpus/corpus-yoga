#!/usr/bin/env bash
# Convert and validate Claude Code CLI session transcripts.
#
# Usage:
#   ./src/main/code-projects/RUNME.sh --code-project  <path>
#   ./src/main/code-projects/RUNME.sh --code-projects <path>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/code-projects"

parse_args() {
  code_project=""
  code_projects=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --code-project)  code_project="$2";  shift 2 ;;
      --code-projects) code_projects="$2"; shift 2 ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --code-project <path> | --code-projects <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$code_project" && -z "$code_projects" ]]; then
    echo "Usage: $0 --code-project <path/to/project-directory>"
    echo "       $0 --code-projects <path/to/code-projects-root>"
    echo
    echo "  project-directory: a subdirectory of ext/code-projects/, e.g.:"
    echo "    ext/code-projects/\$(pwd | tr '/' '-')"
    echo "Pass --help for more information."
    exit 1
  fi
}

run_one() {
  local jsonl="$1" project_name="$2"
  local session; session="$(basename "${jsonl%.jsonl}")"
  local out_dir="$OUTPUT_DIR/$project_name/$session"
  mkdir -p "$out_dir"
  "$SCRIPT_DIR/jsonl_to_json.sh" "$jsonl" "$out_dir/session.json"
  "$SCRIPT_DIR/validate.sh" --code-project-session "$out_dir"
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  local dirs=()
  if [[ -n "$code_project" ]]; then
    dirs=("$(cd "$code_project" && pwd)")
  else
    for d in "$(cd "$code_projects" && pwd)"/-Users-*/; do
      [[ -d "$d" ]] || continue
      dirs+=("$d")
    done
  fi

  for project_dir in "${dirs[@]}"; do
    local name; name="$(basename "${project_dir%/}")"
    echo "$name"
    rm -rf "${OUTPUT_DIR:?}/$name"
    local found=0
    for jsonl in "${project_dir%/}"/*.jsonl; do
      [[ -f "$jsonl" ]] || continue
      found=1
      run_one "$jsonl" "$name"
    done
    [[ "$found" -eq 1 ]] || echo "  (no .jsonl files found)"
  done
}

main "$@"
