#!/usr/bin/env bash
# Capture all conversations from claude.ai and gemini.google.com into ext/browser-captures/.
# Requires Safari open, focused, and logged into both sites throughout.
# Captures run in their own tab; the user's front tab is restored afterwards.
#
# Usage:
#   src/main/browser-captures/PREP.sh                  # claude api, gemini dom
#   src/main/browser-captures/PREP.sh --new-claude-scrape  # also DOM-scrape claude (for compare_markdown)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

main() {
  local new_claude_scrape=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --new-claude-scrape) new_claude_scrape="--scrape"; shift ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done

  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  mkdir -p "$REPO_DIR/ext/browser-captures/claude"
  mkdir -p "$REPO_DIR/ext/browser-captures/gemini"

  # Capture-health baseline before the run — the before/after delta lands in the same
  # log. Suspects here are the reason to capture, not an error.
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_captures.py" \
    --browser-captures "$REPO_DIR/ext/browser-captures" \
    --api "$REPO_DIR/lib/markdown/claude/conversations" || true
  # Capture both agents regardless of either failing, then surface a non-zero exit if either did
  # (don't let a claude failure abort the gemini capture). Claude is api-only unless --new-claude-scrape.
  local rc=0
  "$SCRIPT_DIR/safari_capture.sh" --agent claude ${new_claude_scrape:+"$new_claude_scrape"} || rc=$?
  "$SCRIPT_DIR/safari_capture.sh" --agent gemini || rc=$?
  return $rc
}

main "$@"
