#!/usr/bin/env bash
# Validate browser-captured API JSON files against the apiConversation schema.
#
# Usage:
#   ./src/main/browser-captures/claude/RUNME.sh --browser-capture ext/browser-captures/claude/<uuid>
#   ./src/main/browser-captures/claude/RUNME.sh --browser-captures ext/browser-captures/claude

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

parse_args() {
  browser_capture=""
  browser_captures=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --browser-capture)  browser_capture="$2";  shift 2 ;;
      --browser-captures) browser_captures="$2"; shift 2 ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --browser-capture <path> | --browser-captures <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$browser_capture" && -z "$browser_captures" ]]; then
    echo "Usage: $0 --browser-capture <path/to/uuid-directory>"
    echo "       $0 --browser-captures <path/to/browser-captures>"
    echo "Pass --help for more information."
    exit 1
  fi
}

run_one() {
  local input_dir="${1%/}"
  "$SCRIPT_DIR/validate.sh" --browser-capture "$input_dir"
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$browser_capture" ]]; then
    run_one "$(cd "$browser_capture" && pwd)"
  else
    local root; root="$(cd "$browser_captures" && pwd)"
    local found=0
    for d in "$root"/*/; do
      [[ -d "$d" ]] || continue
      found=1
      run_one "$d"
    done
    [[ $found -eq 0 ]] && echo "no captures in $root"
  fi
}

main "$@"
