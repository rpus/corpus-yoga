#!/usr/bin/env bash
# Verify that data/input/claude/chat/bulk-export/ contains at least one bulk export.
#
# If no exports are found, prints a skip notice and exits zero — a missing bulk
# export is not an error; the pipeline simply has nothing to do.
# No network access, no writes, no interactive steps — a prerequisite check only.
#
# To download a bulk export:
#   1. Log in to https://claude.ai
#   2. Settings → Privacy → Export Data → Export (All)
#   3. Click the download link in the emailed confirmation
#   4. Extract the downloaded archive into data/input/claude/chat/bulk-export/
#
# Usage:
#   src/main/chat-exports/PREP.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

check_exports() {
  local ext_dir="$REPO_DIR/data/input/claude/chat/bulk-export"
  for d in "$ext_dir"/data-*/; do
    [[ -d "$d" ]] && return 0
  done
  echo "skipping chat-exports (no bulk export in data/input/claude/chat/bulk-export/ — download from https://claude.ai/settings/data-privacy-controls)"
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  check_exports
}

main "$@"
