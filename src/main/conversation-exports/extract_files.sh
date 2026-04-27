#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   src/main/conversation-exports/extract_files.sh --conversation-export ../conversation-exports/data-2026-04-07-07-52-05-batch-0000
#   src/main/conversation-exports/extract_files.sh --conversation-exports ../conversation-exports

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/conversation-exports"

run_one() {
  local d="${1%/}"
  local name; name="$(basename "$d")"
  local log_path="$OUTPUT_DIR/$name/extracted_files/extract_files.log"
  mkdir -p "$(dirname "$log_path")"
  python "$SCRIPT_DIR/extract_files.py" --conversation-export "$d" >> "$log_path" 2>&1
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //" | head -10
  exit 0
fi

main() {
  local conversation_export="" conversation_exports=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --conversation-export)  conversation_export="$2";  shift 2 ;;
      --conversation-exports) conversation_exports="$2"; shift 2 ;;
      *) echo "Unknown argument: $1"
         echo "Usage: $0 --conversation-export <path> | --conversation-exports <path>"
         echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$conversation_export" && -z "$conversation_exports" ]]; then
    echo "Usage: $0 --conversation-export <path/to/data-directory>"
    echo "       $0 --conversation-exports <path/to/conversation-exports>"
    echo "       Pass --help for more information."
    exit 1
  fi

  # shellcheck source=/dev/null
  source ~/venvs/general/bin/activate

  if [[ -n "$conversation_export" ]]; then
    run_one "$(cd "$conversation_export" && pwd)"
  else
    for d in "$(cd "$conversation_exports" && pwd)"/data-*/; do
      run_one "$d"
    done
  fi

  deactivate
}

main "$@"
