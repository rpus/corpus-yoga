#!/usr/bin/env bash
# Capture Claude.ai or Gemini conversations via Safari automation.
#
# Two modes (orthogonal to the invoker — CLI, browser.sh, or the macOS Shortcut):
#   (no args)     Discover and capture all conversations, navigating in a work tab.
#   --provider <p>  claude | gemini. Named provider, not "agent": `corpus-yoga agent` is the
#                   code-agent session store, an unrelated thing, and one word cannot
#                   mean both — and capture.py takes --provider too.
#   --mechanism <m> API | DOM. Restricts; forwarded unread. Default: every mechanism
#                   the provider has.
#   --id <id>     Capture one conversation — in place if the front tab shows it, else navigated to.
#
# Usage:
#   src/main/cli/browser/capture.sh --provider claude
#   src/main/cli/browser/capture.sh --provider claude --mechanism DOM
#   src/main/cli/browser/capture.sh --provider claude --id <uuid>
#   src/main/cli/browser/capture.sh --provider gemini
#   src/main/cli/browser/capture.sh --provider gemini --id <id>

set -euo pipefail

SELF='src/main/cli/browser/capture.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_DIR/src/main/tier.sh"

main() {
  # --progress: the artifact the capture narrative is written to, one line per step
  # (issues/413), named by the caller (browser.sh, by the launcher's stamp - issues/708); without it,
  # a direct run, this file names one by its own stamp. The record of the act is the
  # launcher's tee; the terminal and the record keep the anchors.
  local progress=""
  if [[ "${1-}" == "--progress" ]]; then progress="$2"; shift 2; fi
  local provider=""
  case "${1-}" in
    --provider) provider="$2"; shift 2 ;;
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "Usage: $0 [--progress <path>] --provider claude|gemini [--id <id>]" >&2; exit 1 ;;
  esac
  if [[ "$provider" != "claude" && "$provider" != "gemini" ]]; then
    echo "Usage: $0 [--progress <path>] --provider claude|gemini [--id <id>]" >&2; exit 1
  fi
  echo "src/main/cli/browser/$(basename "$0") ($provider)"
  local log rc=0
  log="${progress:-$TMP_DIR/logs/browser/capture/$(stamp_of browser capture).$provider.progress}"
  mkdir -p "$(dirname "$log")"
  # Name the progress artifact FIRST: a Shortcut invocation shows this output in a
  # transient dialog (if at all), and any 'see the progress' advice is useless unless its
  # path has been said out loud somewhere durable-feeling.
  echo "progress: ${log#"$REPO_DIR/"}"
  # No tee (issues/413, issues/415): the python owns both channels — the full narrative goes
  # to the progress artifact (line-buffered, anchored before any work), the terminal
  # gets the anchor, one line per conversation, and the verdict. A pipe here once
  # held the whole story in a buffer a ctrl-C erased while the terminal had
  # shown it — the 0-byte-log class.
  caffeinate -dim "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/capture.py" \
    --provider "$provider" --progress "$log" "$@" || rc=$?
  return $rc
}

main "$@"
