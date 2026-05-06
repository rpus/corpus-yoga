#!/usr/bin/env bash
# Validate captured API JSON files against the apiConversation schema.
#
# Usage:
#   src/main/browser-captures/validate.sh --batch <path>
#   src/main/browser-captures/validate.sh --batches <path>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMA="$REPO_DIR/rsc/schema/apiConversation/v1.json"
OUTPUT_DIR="$REPO_DIR/gen/browser-captures"

validate_conversation() {
  local json="$1" batch_name="$2"
  local uuid; uuid="$(basename "$(dirname "$json")")"
  local out_dir="$OUTPUT_DIR/$batch_name/$uuid"
  local log_out="$out_dir/validation/apiConversation/v1.log"
  mkdir -p "$out_dir" "$(dirname "$log_out")"

  {
    date -Iseconds
    echo "$json: $(wc -c < "$json" | xargs) bytes"
    echo "$SCHEMA: $(wc -c < "$SCHEMA" | xargs) bytes"
    python "$REPO_DIR/src/main/validate.py" "$json" "$SCHEMA"
  } > "$log_out"

  local status; status="$(grep -E '^Valid!|^Validation error' "$log_out" | head -1)"
  echo "  $uuid: $status"
}

validate_batch() {
  local batch_dir="${1%/}"
  local batch_name; batch_name="$(basename "$batch_dir")"
  echo "$batch_name"

  local found=0
  for uuid_dir in "$batch_dir"/*/; do
    [ -d "$uuid_dir" ] || continue
    for json in "$uuid_dir"/*.json; do
      [ -f "$json" ] || continue
      found=1
      validate_conversation "$json" "$batch_name"
    done
  done

  if [[ "$found" -eq 0 ]]; then
    echo "  (no JSON files found)"
  fi
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //"
  exit 0
fi

main() {
  local batch="" batches=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --batch)   batch="$2";   shift 2 ;;
      --batches) batches="$2"; shift 2 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --batch <path> | --batches <path>"
        exit 1 ;;
    esac
  done

  if [[ -z "$batch" && -z "$batches" ]]; then
    echo "Usage: $0 --batch <path/to/batch-directory>"
    echo "       $0 --batches <path/to/browser-captures>"
    exit 1
  fi

  # shellcheck source=/dev/null
  source "$REPO_DIR/src/activate_venv.sh"

  if [[ -n "$batch" ]]; then
    validate_batch "$(cd "$batch" && pwd)"
  else
    for d in "$(cd "$batches" && pwd)"/data-*/; do
      [ -d "$d" ] || continue
      validate_batch "$d"
    done
  fi
}

main "$@"
