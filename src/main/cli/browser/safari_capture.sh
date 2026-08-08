#!/usr/bin/env bash
# Capture Claude.ai or Gemini conversations via Safari automation.
#
# Two modes (orthogonal to the invoker — CLI, browser.sh, or the macOS Shortcut):
#   (no args)     Discover and capture all conversations, navigating in a work tab.
#   --provider <p>  claude | gemini. Named provider, not "agent": `yoga agent` is the
#                   code-agent session store, an unrelated thing, and one word cannot
#                   mean both — and safari_capture.py takes --provider too.
#   --mechanism <m> API | DOM. Restricts; forwarded unread. Default: every mechanism
#                   the provider has.
#   --id <id>     Capture one conversation — in place if the front tab shows it, else navigated to.
#
# Usage:
#   src/main/cli/browser/safari_capture.sh --provider claude
#   src/main/cli/browser/safari_capture.sh --provider claude --mechanism DOM
#   src/main/cli/browser/safari_capture.sh --provider claude --id <uuid>
#   src/main/cli/browser/safari_capture.sh --provider gemini
#   src/main/cli/browser/safari_capture.sh --provider gemini --id <id>

set -euo pipefail

SELF='src/main/cli/browser/safari_capture.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

main() {
  local provider=""
  case "${1-}" in
    --provider) provider="$2"; shift 2 ;;
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "Usage: $0 --provider claude|gemini [--id <id>]" >&2; exit 1 ;;
  esac
  if [[ "$provider" != "claude" && "$provider" != "gemini" ]]; then
    echo "Usage: $0 --provider claude|gemini [--id <id>]" >&2; exit 1
  fi
  echo "src/main/cli/browser/$(basename "$0") ($provider)"
  local log rc=0
  log="$REPO_DIR/tmp/logs/browser/capture/$provider/$(date -u '+%Y-%m-%dT%H%M%SZ').log"
  mkdir -p "$(dirname "$log")"
  # Name the log FIRST: a Shortcut invocation shows this output in a transient
  # dialog (if at all), and any 'see the run log' advice is useless unless the
  # log's own path has been said out loud somewhere durable-feeling.
  echo "Log: $log"
  # No tee (#413/#415): the python owns both channels — the full narrative goes
  # to the run log (line-buffered, anchored before any work), the terminal gets
  # the anchor, one line per conversation, and the verdict. A pipe here once
  # held the whole story in a buffer a ctrl-C erased while the terminal had
  # shown it — the 0-byte-log class.
  caffeinate -dim "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/safari_capture.py" \
    --provider "$provider" --run-log "$log" "$@" || rc=$?
  echo "Log: $log"
  return $rc
}

main "$@"
