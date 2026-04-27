#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   ./src/main/conversation-exports/RUNME.sh --conversation-exports ../conversation-exports
#   ./src/main/conversation-exports/RUNME.sh --conversation-export ../conversation-exports/data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776550128-b9e6a9cd-batch-0000
#   ./src/main/conversation-exports/RUNME.sh --conversation-exports ../conversation-exports --pay-for-inference

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/conversation-exports"

run_one() {
  local export_dir="${1%/}"
  local name; name="$(basename "$export_dir")"

  rm -rf "${OUTPUT_DIR:?}/$name"

  "$SCRIPT_DIR/validate.sh"       --conversation-export "$export_dir"
  "$SCRIPT_DIR/extract_files.sh"  --conversation-export "$export_dir"
  "$SCRIPT_DIR/extract_heredocs.sh" --conversation-export "$export_dir"

  if [[ "$pay_for_inference" == "1" ]]; then
    "$SCRIPT_DIR/infer_tables.sh" --conversation-export "$export_dir"
  fi

  "$SCRIPT_DIR/present.sh" --conversation-export "$export_dir"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //" | head -10
  exit 0
fi

main() {
  local conversation_export="" conversation_exports="" pay_for_inference="0"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --conversation-export)        conversation_export="$2";      shift 2 ;;
      --conversation-exports)       conversation_exports="$2";     shift 2 ;;
      --pay-for-inference)  pay_for_inference="1"; shift   ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --conversation-export <path> | --conversation-exports <path> [--pay-for-inference]"
        echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$conversation_export" && -z "$conversation_exports" ]]; then
    echo "Usage: $0 --conversation-export <path/to/single-export>"
    echo "       $0 --conversation-exports <path/to/conversation-exports>"
    echo
    echo "Options:"
    echo "  --pay-for-inference   also run infer_tables.sh (requires ANTHROPIC_API_KEY in env)"
    echo "       Pass --help for more information."
    exit 1
  fi

  if [[ -n "$conversation_export" ]]; then
    run_one "$(cd "$conversation_export" && pwd)"
  else
    for d in "$(cd "$conversation_exports" && pwd)"/*/; do
      run_one "$d"
    done
  fi
}

main "$@"
