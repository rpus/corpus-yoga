#!/usr/bin/env bash
# Capture all conversations from claude.ai and gemini.google.com into ext/browser-captures/.
# Requires Safari open, focused, and logged into both sites throughout.
#
# Usage:
#   src/main/browser-captures/PREP.sh                  # claude api, gemini dom
#   src/main/browser-captures/PREP.sh --scrape-claude  # also DOM-scrape claude (for compare_markdown)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

main() {
  local scrape_claude=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --scrape-claude) scrape_claude="--scrape"; shift ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done

  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  mkdir -p "$REPO_DIR/ext/browser-captures/claude"
  mkdir -p "$REPO_DIR/ext/browser-captures/gemini"
  # Capture both agents regardless of either failing, then surface a non-zero exit if either did
  # (don't let a claude failure abort the gemini capture). Claude is api-only unless --scrape-claude.
  local rc=0
  "$SCRIPT_DIR/safari_capture.sh" --agent claude ${scrape_claude:+"$scrape_claude"} || rc=$?
  "$SCRIPT_DIR/safari_capture.sh" --agent gemini || rc=$?
  return $rc
}

main "$@"
