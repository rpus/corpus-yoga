#!/usr/bin/env bash
# Link browser captures into the chat-exports gen tree for conversations that have them.
#
# For each UUID in a chat export's conversations.json, creates a symlink:
#   gen/chat-exports/<export>/browser-captures/<uuid> -> ext/browser-captures/<uuid>
#
# Only links UUIDs that have an existing capture directory. Safe to re-run.
#
# Usage:
#   src/main/chat-exports/link_browser_captures.sh --chat-export <path>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/chat-exports"
CAPTURES_DIR="$REPO_DIR/ext/browser-captures/claude"

link_captures() {
  local chat_export="${1%/}"
  local name; name="$(basename "$chat_export")"
  local conversations_json="$chat_export/conversations.json"
  local links_dir="$OUTPUT_DIR/$name/browser-captures"

  [[ -f "$conversations_json" ]] || return

  local linked=0
  while IFS= read -r uuid; do
    local capture_dir="$CAPTURES_DIR/$uuid"
    [[ -d "$capture_dir" ]] || continue
    mkdir -p "$links_dir"
    ln -sfn "$capture_dir" "$links_dir/$uuid"
    (( linked++ )) || true
  done < <(jq -r '.[].uuid' "$conversations_json")

  echo "  linked $linked browser captures"
}

parse_args() {
  chat_export=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export) chat_export="$2"; shift 2 ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --chat-export <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$chat_export" ]]; then
    echo "Usage: $0 --chat-export <path/to/export-directory>"
    echo "Pass --help for more information."
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  link_captures "$(cd "$chat_export" && pwd)"
}

main "$@"
