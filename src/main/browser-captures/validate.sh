#!/usr/bin/env bash
# Validate a single browser-capture conversation against the apiConversation schema.
#
# Usage:
#   src/main/browser-captures/validate.sh --browser-capture <path/to/uuid-directory>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMA_DIR="$REPO_DIR/rsc/schema/browser-captures/apiConversation"
OUTPUT_DIR="$REPO_DIR/gen/browser-captures"

validate_conversation() {
  local uuid_dir="${1%/}"
  local uuid; uuid="$(basename "$uuid_dir")"
  local out_dir="$OUTPUT_DIR/$uuid"

  local found=0
  for json in "$uuid_dir"/*.json; do
    [[ -f "$json" ]] || continue
    found=1
    "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
      "$json" "$SCHEMA_DIR" "$out_dir/validation/apiConversation" "$uuid"
  done

  if [[ "$found" -eq 0 ]]; then
    echo "  (no JSON files found)"
  fi
}

parse_args() {
  browser_capture=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --browser-capture) browser_capture="$2"; shift 2 ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --browser-capture <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$browser_capture" ]]; then
    echo "Usage: $0 --browser-capture <path/to/uuid-directory>"
    echo "Pass --help for more information."
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  validate_conversation "$(cd "$browser_capture" && pwd)"
}

main "$@"
