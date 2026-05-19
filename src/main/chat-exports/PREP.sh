#!/usr/bin/env bash
# Verify that ext/chat-exports/ contains at least one bulk export.
#
# If no exports are found, prints setup instructions and exits non-zero.
# No network access or interactive steps — this is a prerequisite check only.
#
# To download a bulk export:
#   1. Log in to https://claude.ai
#   2. Settings → Privacy → Export Data → Export (All)
#   3. Click the download link in the emailed confirmation
#   4. Extract the downloaded archive into ext/chat-exports/
#
# Usage:
#   src/main/chat-exports/PREP.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

check_exports() {
  local ext_dir="$REPO_DIR/ext/chat-exports"
  for d in "$ext_dir"/data-*/; do
    [[ -d "$d" ]] && return 0
  done
  grep "^# " "$0" | sed "s/^# //"
  exit 1
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  check_exports
}

main "$@"
