#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   ./src/main/chat-exports/RUNME.sh --chat-exports ../chat-exports
#   ./src/main/chat-exports/RUNME.sh --chat-export ../chat-exports/data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776550128-b9e6a9cd-batch-0000
#   ./src/main/chat-exports/RUNME.sh --chat-exports ../chat-exports --pay-for-inference

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/chat-exports"

run_one() {
  local export_dir="${1%/}"
  local name; name="$(basename "$export_dir")"

  rm -rf "${OUTPUT_DIR:?}/$name"

  "$SCRIPT_DIR/validate.sh"         --chat-export "$export_dir"
  "$SCRIPT_DIR/extract_files.sh"    --chat-export "$export_dir"
  "$SCRIPT_DIR/extract_heredocs.sh" --chat-export "$export_dir"

  if [[ "$pay_for_inference" == "1" ]]; then
    "$SCRIPT_DIR/infer_tables.sh"   --chat-export "$export_dir"
  fi

  "$SCRIPT_DIR/present.sh"          --chat-export "$export_dir"
  "$SCRIPT_DIR/audit_files.sh"      --chat-export "$export_dir"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //" | head -10
  exit 0
fi

main() {
  local chat_export="" chat_exports="" pay_for_inference="0"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export)        chat_export="$2";      shift 2 ;;
      --chat-exports)       chat_exports="$2";     shift 2 ;;
      --pay-for-inference)  pay_for_inference="1"; shift   ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --chat-export <path> | --chat-exports <path> [--pay-for-inference]"
        echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$chat_export" && -z "$chat_exports" ]]; then
    echo "Usage: $0 --chat-export <path/to/single-export>"
    echo "       $0 --chat-exports <path/to/chat-exports>"
    echo
    echo "Options:"
    echo "  --pay-for-inference   also run infer_tables.sh (requires ANTHROPIC_API_KEY in env)"
    echo "       Pass --help for more information."
    exit 1
  fi

  if [[ -n "$chat_export" ]]; then
    run_one "$(cd "$chat_export" && pwd)"
  else
    for d in "$(cd "$chat_exports" && pwd)"/data-*/; do
      [ -d "$d" ] || continue
      run_one "$d"
    done
  fi
}

main "$@"
