#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   src/main/pipeline/chat-exports/extract_heredocs.sh --chat-export data/input/claude/chat/bulk-export/data-2026-04-07-07-52-05-batch-0000
#   src/main/pipeline/chat-exports/extract_heredocs.sh --chat-exports data/input/claude/chat/bulk-export

set -euo pipefail

SELF='src/main/pipeline/chat-exports/extract_heredocs.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
CACHE_DIR="$REPO_DIR/tmp/cache/chat-exports"

run_one() {
  local d="${1%/}"
  local name; name="$(basename "$d")"
  local log_path="$CACHE_DIR/$name/extracted_heredocs/extract_heredocs.log"
  mkdir -p "$(dirname "$log_path")"
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/extract_heredocs.py" --chat-export "$d" > "$log_path" 2>&1
}

parse_args() {
  chat_export=""
  chat_exports=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export)  chat_export="$2";  shift 2 ;;
      --chat-exports) chat_exports="$2"; shift 2 ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --chat-export <path> | --chat-exports <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$chat_export" && -z "$chat_exports" ]]; then
    echo "Usage: $0 --chat-export <path/to/data-directory>"
    echo "       $0 --chat-exports <path/to/chat-exports>"
    echo "Pass --help for more information."
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$chat_export" ]]; then
    run_one "$(cd "$chat_export" && pwd)"
  else
    for d in "$(cd "$chat_exports" && pwd)"/data-*/; do
      run_one "$d"
    done
  fi
}

main "$@"
