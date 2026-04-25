#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   ./RUNME.sh --data-root ../data-exports
#   ./RUNME.sh --data-dir ../data-exports/data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776550128-b9e6a9cd-batch-0000
#   ./RUNME.sh --data-root ../data-exports --pay-for-inference

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/gen"

run_one() {
  local data_dir="${1%/}"
  local name; name="$(basename "$data_dir")"

  rm -rf "${OUTPUT_DIR:?}/$name"

  "$SCRIPT_DIR/src/main/validate.sh"       --data-dir "$data_dir"
  "$SCRIPT_DIR/src/main/extract_files.sh"  --data-dir "$data_dir"
  "$SCRIPT_DIR/src/main/extract_heredocs.sh" --data-dir "$data_dir"

  if [[ "$pay_for_inference" == "1" ]]; then
    "$SCRIPT_DIR/src/main/infer_tables.sh" --data-dir "$data_dir"
  fi

  "$SCRIPT_DIR/src/main/present.sh" --data-dir "$data_dir"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //" | head -10
  exit 0
fi

main() {
  local data_dir="" data_root="" pay_for_inference="0"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --data-dir)           data_dir="$2";        shift 2 ;;
      --data-root)          data_root="$2";       shift 2 ;;
      --pay-for-inference)  pay_for_inference="1"; shift   ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --data-dir <path> | --data-root <path> [--pay-for-inference]"
        echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$data_dir" && -z "$data_root" ]]; then
    echo "Usage: $0 --data-dir <path/to/data-directory>"
    echo "       $0 --data-root <path/to/data-exports>"
    echo
    echo "Options:"
    echo "  --pay-for-inference   also run infer_tables.sh (requires ANTHROPIC_API_KEY in env)"
    echo "       Pass --help for more information."
    exit 1
  fi

  if [[ -n "$data_dir" ]]; then
    run_one "$(cd "$data_dir" && pwd)"
  else
    for d in "$(cd "$data_root" && pwd)"/data-*/; do
      run_one "$d"
    done
  fi
}

main "$@"
