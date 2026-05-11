#!/usr/bin/env bash
# Validate a single browser-capture batch against the apiConversation schema.
#
# Usage:
#   src/main/browser-captures/validate.sh --browser-capture <path/to/batch-directory>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMA_DIR="$REPO_DIR/rsc/schema/browser-captures/apiConversation"
OUTPUT_DIR="$REPO_DIR/gen/browser-captures"

# shellcheck source=/dev/null
source "$REPO_DIR/src/main/validate_versions.sh"

validate_conversation() {
  local json="$1" batch_name="$2"
  local uuid; uuid="$(basename "$(dirname "$json")")"
  local out_dir="$OUTPUT_DIR/$batch_name/$uuid"

  validate_versions "$json" "$SCHEMA_DIR" "$out_dir/validation/apiConversation" "$uuid"
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
  local browser_capture=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --browser-capture) browser_capture="$2"; shift 2 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --browser-capture <path>"
        echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$browser_capture" ]]; then
    echo "Usage: $0 --browser-capture <path/to/batch-directory>"
    echo "       Pass --help for more information."
    exit 1
  fi

  # shellcheck source=/dev/null
  source "$REPO_DIR/src/activate_venv.sh"

  validate_batch "$(cd "$browser_capture" && pwd)"
}

main "$@"
