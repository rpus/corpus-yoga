#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   src/main/chat-exports/extract_heredocs.sh --chat-export ../chat-exports/data-2026-04-07-07-52-05-batch-0000
#   src/main/chat-exports/extract_heredocs.sh --chat-exports ../chat-exports

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/chat-exports"

run_one() {
  local d="${1%/}"
  local name; name="$(basename "$d")"
  local log_path="$OUTPUT_DIR/$name/extracted_heredocs/extract_heredocs.log"
  mkdir -p "$(dirname "$log_path")"
  python "$SCRIPT_DIR/extract_heredocs.py" --chat-export "$d" > "$log_path" 2>&1
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //" | head -10
  exit 0
fi

main() {
  local chat_export="" chat_exports=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export)  chat_export="$2";  shift 2 ;;
      --chat-exports) chat_exports="$2"; shift 2 ;;
      *) echo "Unknown argument: $1"
         echo "Usage: $0 --chat-export <path> | --chat-exports <path>"
         echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$chat_export" && -z "$chat_exports" ]]; then
    echo "Usage: $0 --chat-export <path/to/data-directory>"
    echo "       $0 --chat-exports <path/to/chat-exports>"
    echo "       Pass --help for more information."
    exit 1
  fi

  # shellcheck source=/dev/null
  source "$REPO_DIR/src/activate_venv.sh"

  if [[ -n "$chat_export" ]]; then
    run_one "$(cd "$chat_export" && pwd)"
  else
    for d in "$(cd "$chat_exports" && pwd)"/data-*/; do
      run_one "$d"
    done
  fi
}

main "$@"
