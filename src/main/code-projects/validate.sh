#!/usr/bin/env bash
# Validate a single converted Claude Code CLI session against all schema versions.
#
# Usage:
#   src/main/code-projects/validate.sh --code-project-session <path/to/session-dir>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMA_DIR="$REPO_DIR/rsc/schema/code-projects/session"

parse_args() {
  session_dir=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --code-project-session) session_dir="$2"; shift 2 ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --code-project-session <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$session_dir" ]]; then
    echo "Usage: $0 --code-project-session <path/to/session-directory>"
    echo "Pass --help for more information."
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  local session; session="$(basename "$session_dir")"
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
    "$session_dir/session.json" "$SCHEMA_DIR" "$session_dir/validation/session" "$session"
}

main "$@"
