#!/usr/bin/env bash
# Validate converted Claude Code CLI data against all schema versions.
#
# Usage:
#   src/main/pipeline/code-agents/validate.sh --code-agent-session <path/to/session-dir>
#   src/main/pipeline/code-agents/validate.sh --code-agent-memory  <path/to/cache-memory-dir>
#
# A session dir holds two data: session.json (the session family) and
# conversation.json (its sessionConversation projection); both validate here.
# A cache memory dir holds memory.json (the projectMemory family).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SCHEMA_ROOT="$REPO_DIR/rsc/schema/code-agents"

parse_args() {
  session_dir=""
  memory_dir=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --code-agent-session) session_dir="$2"; shift 2 ;;
      --code-agent-memory)  memory_dir="$2";  shift 2 ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --code-agent-session <path> | --code-agent-memory <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$session_dir" && -z "$memory_dir" ]]; then
    echo "Usage: $0 --code-agent-session <path/to/session-directory>"
    echo "       $0 --code-agent-memory  <path/to/cache-memory-directory>"
    echo "Pass --help for more information."
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  if [[ -n "$session_dir" ]]; then
    local session; session="$(basename "$session_dir")"
    "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
      "$session_dir/session.json" "$SCHEMA_ROOT/session" \
      "$session_dir/validation/session" "$session"
    "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
      "$session_dir/conversation.json" "$SCHEMA_ROOT/sessionConversation" \
      "$session_dir/validation/sessionConversation" "$session"
  fi
  if [[ -n "$memory_dir" ]]; then
    local project; project="$(basename "$(dirname "$memory_dir")")"
    "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
      "$memory_dir/memory.json" "$SCHEMA_ROOT/projectMemory" \
      "$memory_dir/validation/projectMemory" "$project/memory"
  fi
}

main "$@"
