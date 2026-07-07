#!/usr/bin/env bash
# Convert and validate Claude Code CLI session transcripts.
#
# Usage:
#   ./src/main/code-projects/RUNME.sh --code-project  <path>
#   ./src/main/code-projects/RUNME.sh --code-projects <path>
#   ./src/main/code-projects/RUNME.sh --plan   # print the ordered step list; run nothing
#
# The step lists below (project_housekeeping, run_one) are the ONE authority on
# order: --plan prints exactly the lists that execute (see src/main/steps.sh).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/code-projects"

# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"

parse_args() {
  code_project=""
  code_projects=""
  plan="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --code-project)  code_project="$2";  shift 2 ;;
      --code-projects) code_projects="$2"; shift 2 ;;
      --plan)          plan="1";           shift   ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --code-project <path> | --code-projects <path> | --plan"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ "$plan" == "0" && -z "$code_project" && -z "$code_projects" ]]; then
    echo "Usage: $0 --code-project <path/to/project-directory>"
    echo "       $0 --code-projects <path/to/code-projects-root>"
    echo
    echo "  project-directory: a subdirectory of ext/code-projects/, e.g.:"
    echo "    ext/code-projects/\$(pwd | tr '/' '-')"
    echo "Pass --help for more information."
    exit 1
  fi
}

prune_departed() {
  # No blanket wipe: the validation logs under gen/ ARE the memoisation (an
  # unchanged session revalidates against nothing), and jsonl_to_json keeps
  # session.json's mtime when content is unchanged for the same reason. Only
  # sessions whose .jsonl is gone are pruned.
  local project_dir="$1" name="$2"
  for existing in "$OUTPUT_DIR/$name"/*/; do
    [[ -d "$existing" ]] || continue
    local sess; sess="$(basename "${existing%/}")"
    [[ -f "${project_dir%/}/$sess.jsonl" ]] || rm -rf "${existing:?}"
  done
}

project_housekeeping() {
  step prune_departed_sessions prune_departed "$1" "$2"
}

run_one() {
  local jsonl="$1" project_name="$2"
  local session; session="$(basename "${jsonl%.jsonl}")"
  local out_dir="$OUTPUT_DIR/$project_name/$session"
  step ensure_session_dir mkdir -p "$out_dir"
  step jsonl_to_json      "$SCRIPT_DIR/jsonl_to_json.sh" "$jsonl" "$out_dir/session.json"
  step validate           "$SCRIPT_DIR/validate.sh" --code-project-session "$out_dir"
}

print_plan() {
  echo "code-projects steps — per project directory:"
  project_housekeeping '<project-dir>' '<project>'
  echo "then per session .jsonl within it:"
  run_one '<session>.jsonl' '<project>'
}

main() {
  parse_args "$@"
  if [[ "$plan" == "1" ]]; then print_plan; exit 0; fi
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  local dirs=()
  if [[ -n "$code_project" ]]; then
    dirs=("$(cd "$code_project" && pwd)")
  else
    if [[ ! -d "$code_projects" ]]; then
      echo "no projects in $code_projects (PREP.sh symlinks it to ~/.claude/projects)"
      exit 0
    fi
    for d in "$(cd "$code_projects" && pwd)"/-Users-*/; do
      [[ -d "$d" ]] || continue
      dirs+=("$d")
    done
  fi

  for project_dir in "${dirs[@]}"; do
    local name; name="$(basename "${project_dir%/}")"
    echo "$name"
    project_housekeeping "$project_dir" "$name"
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
