#!/usr/bin/env bash
# Validate browser-captured API JSON files against the apiConversation schema.
#
# Usage:
#   ./src/main/browser-captures/RUNME.sh --browser-capture ../browser-captures/data-<...>
#   ./src/main/browser-captures/RUNME.sh --browser-captures ../browser-captures

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_one() {
  local batch_dir="${1%/}"
  "$SCRIPT_DIR/validate.sh" --browser-capture "$batch_dir"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //"
  exit 0
fi

main() {
  local browser_capture="" browser_captures=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --browser-capture)   browser_capture="$2";   shift 2 ;;
      --browser-captures)  browser_captures="$2";  shift 2 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --browser-capture <path> | --browser-captures <path>"
        echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$browser_capture" && -z "$browser_captures" ]]; then
    echo "Usage: $0 --browser-capture <path/to/batch-directory>"
    echo "       $0 --browser-captures <path/to/browser-captures>"
    echo "       Pass --help for more information."
    exit 1
  fi

  if [[ -n "$browser_capture" ]]; then
    run_one "$(cd "$browser_capture" && pwd)"
  else
    for d in "$(cd "$browser_captures" && pwd)"/data-*/; do
      [ -d "$d" ] || continue
      run_one "$d"
    done
  fi
}

main "$@"
