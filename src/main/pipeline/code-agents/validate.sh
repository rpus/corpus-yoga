#!/usr/bin/env bash
# Validate converted Claude Code CLI data against all schema versions.
#
# Usage:
#   src/main/pipeline/code-agents/validate.sh --code-agent-session <path/to/session-dir>
#   src/main/pipeline/code-agents/validate.sh --code-agent-memory  <path/to/cache-memory-dir>
#   src/main/pipeline/code-agents/validate.sh --enumerate --code-agent-session <dir>
#
# A session dir holds two data: session.json (the session family) and
# conversation.json (its sessionConversation projection); both validate here.
# A cache memory dir holds memory.json (the projectMemory family).
#
# --enumerate prints the datum-version tasks instead of running them (#395):
# one line per pair, tab-separated <input> <schema-file> <log-dir> <label> —
# the arguments of validate_versions.py --pair. This face owns the datum-to-
# schema-family mapping; the dispatcher that consumes the lines owns capacity.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
SCHEMA_ROOT="$REPO_DIR/rsc/schema/code-agents"

parse_args() {
  session_dir=""
  memory_dir=""
  enumerate="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --enumerate)          enumerate="1";    shift   ;;
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

# One line per datum-version pair (#395): the arguments of
# validate_versions.py --pair, tab-separated, versions in listing order.
enumerate_family() {
  local input="$1" family="$2" log_dir="$3" label="$4" schema
  for schema in "$SCHEMA_ROOT/$family"/v*.json; do
    [[ -e "$schema" ]] || continue
    printf '%s\t%s\t%s\t%s\n' "$input" "$schema" "$log_dir" "$label"
  done
}

main() {
  parse_args "$@"
  if [[ "$enumerate" == "1" ]]; then
    if [[ -n "$session_dir" ]]; then
      local session; session="$(basename "$session_dir")"
      enumerate_family "$session_dir/session.json" session \
        "$session_dir/validation/session" "$session"
      enumerate_family "$session_dir/conversation.json" sessionConversation \
        "$session_dir/validation/sessionConversation" "$session"
    fi
    if [[ -n "$memory_dir" ]]; then
      local project; project="$(basename "$(dirname "$memory_dir")")"
      enumerate_family "$memory_dir/memory.json" projectMemory \
        "$memory_dir/validation/projectMemory" "$project/memory"
    fi
    return 0
  fi
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
