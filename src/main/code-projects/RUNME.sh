#!/usr/bin/env bash
# Convert and validate Claude Code CLI session transcripts.
#
# Usage:
#   ./src/main/code-projects/RUNME.sh --code-project <path>
#   ./src/main/code-projects/RUNME.sh --code-projects <path>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/code-projects"

run_one() {
  local project_dir="${1%/}"
  local name; name="$(basename "$project_dir")"
  echo "$name"

  rm -rf "${OUTPUT_DIR:?}/$name"

  "$SCRIPT_DIR/validate.sh" --code-project "$project_dir"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //"
  exit 0
fi

main() {
  local code_project="" code_projects=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --code-project)   code_project="$2";   shift 2 ;;
      --code-projects)  code_projects="$2";  shift 2 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --code-project <path> | --code-projects <path>"
        echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$code_project" && -z "$code_projects" ]]; then
    echo "Usage: $0 --code-project <path/to/project-directory>"
    echo "       $0 --code-projects <path/to/code-projects-root>"
    echo
    echo "  project-directory: a subdirectory of ../code-projects/, e.g.:"
    echo "    ../code-projects/\$(pwd | tr '/' '-')"
    echo "       Pass --help for more information."
    exit 1
  fi

  if [[ -n "$code_project" ]]; then
    run_one "$(cd "$code_project" && pwd)"
  else
    for d in "$(cd "$code_projects" && pwd)"/-Users-*/; do
      [ -d "$d" ] || continue
      run_one "$d"
    done
  fi
}

main "$@"
