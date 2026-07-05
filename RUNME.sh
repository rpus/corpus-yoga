#!/usr/bin/env bash
# RUNME.sh — Process all Claude data exports.
#
# Runs three pipelines against their sibling input directories:
#
#   chat-exports     ext/chat-exports/      claude.ai bulk exports, conversations.json etc. (you unzip downloads here)
#   code-projects    ext/code-projects/     Claude Code CLI sessions (symlinked to ~/.claude/projects/ by its PREP.sh)
#   browser-captures ext/browser-captures/  Per-conversation captures (written by --capture-from-browser):
#                                           claude/ live API JSON (validated + projected to markdown);
#                                           gemini/ DOM-scraped markdown (terminal artifact — no API, nothing to validate)
#
# Any ext/ entry may instead be a hand-made symlink, to keep the data outside the clone.
#
# Each pipeline validates its inputs against all schema versions, then (for chat-exports)
# extracts files, infers tables, and renders a dashboard.
#
# Usage:
#   ./RUNME.sh                                      # all pipelines (claude api, gemini dom)
#   ./RUNME.sh --capture-from-browser               # also capture/update via Safari (slow)
#   ./RUNME.sh --capture-from-browser --new-claude-scrape  # also DOM-scrape claude + check projection vs scrape
#   ./RUNME.sh --pay-for-inference                  # also run infer_tables.sh for chat-exports (costs money)
#   ./RUNME.sh --capture-from-browser --pay-for-inference
#
# After running, check results with:
#   src/test/pre_commit.sh            # full check suite; read via: git diff --cached src/test/pre_commit.log

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${VENV:=$HOME/venvs/general}"

parse_args() {
  pay_for_inference=""
  browser_captures=""
  new_claude_scrape=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --pay-for-inference) pay_for_inference="--pay-for-inference"; shift ;;
      --capture-from-browser) browser_captures="1";                   shift ;;
      --new-claude-scrape) new_claude_scrape="--new-claude-scrape";               shift ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Usage: $0 [--capture-from-browser] [--new-claude-scrape] [--pay-for-inference]"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

require_cmd() {
  local cmd="$1" hint="$2"
  if ! command -v "$cmd" &>/dev/null; then
    echo "error: $cmd not found — $hint" >&2
    exit 1
  fi
}

find_python3() {
  if command -v python3 &>/dev/null; then
    echo "python3"; return 0
  fi
  if command -v python &>/dev/null; then
    if python --version 2>&1 | grep -q "^Python 3"; then
      echo "python"; return 0
    fi
  fi
  echo "error: Python 3 not found — install via: brew install python" >&2
  return 1
}

ensure_venv() {
  local python="$1"
  if [[ ! -f "$VENV/bin/activate" ]]; then
    echo "creating venv at $VENV"
    "$python" -m venv "$VENV"
  fi
}

install_deps() {
  # shellcheck source=/dev/null
  source "$VENV/bin/activate"
  echo "checking for pip upgrade"
  pip install --upgrade pip
  pip install -q -r "$SCRIPT_DIR/src/requirements.txt"
}

prep_pipeline() {
  local name="$1"; shift
  echo "── prep: ${name} ────────────────────────────────────────────────────────────"
  local rc=0
  "$SCRIPT_DIR/src/main/${name}/PREP.sh" "$@" || rc=$?
  echo ""
  return $rc
}

run_pipeline() {
  local name="$1"; shift
  echo "── ${name} ──────────────────────────────────────────────────────────────────"
  local rc=0
  "$SCRIPT_DIR/src/main/$name/RUNME.sh" "--${name}" "$@" || rc=$?
  echo ""
  return $rc
}

run_pipeline_safe() {
  local name="$1"; shift
  if ! run_pipeline "$name" "$@"; then
    pipeline_failures+=("$name")
  fi
}

prep_pipeline_safe() {
  local name="$1"; shift
  if ! prep_pipeline "$name" "$@"; then
    pipeline_failures+=("$name (prep)")
  fi
}

LOG_FILE="$SCRIPT_DIR/logs/RUNME/$(date -u '+%Y-%m-%dT%H:%M:%SZ').log"

main() {
  parse_args "$@"
  echo "$(basename "$0") $* — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  require_cmd jq "install via: brew install jq"
  local python; python="$(find_python3)"
  ensure_venv "$python"
  install_deps

  local -a pipeline_failures=()

  [[ -n "$browser_captures" ]] && prep_pipeline_safe browser-captures ${new_claude_scrape:+"$new_claude_scrape"}
  run_pipeline_safe  browser-captures "$SCRIPT_DIR/ext/browser-captures/claude" ${new_claude_scrape:+"$new_claude_scrape"}

  prep_pipeline_safe chat-exports
  run_pipeline_safe  chat-exports "$SCRIPT_DIR/ext/chat-exports" ${pay_for_inference:+"$pay_for_inference"}

  prep_pipeline_safe code-projects
  run_pipeline_safe  code-projects "$SCRIPT_DIR/ext/code-projects"

  echo "── done $(date -u '+%Y-%m-%dT%H:%M:%SZ') ───────────────────────────────────────────"
  if [[ ${#pipeline_failures[@]} -eq 0 ]]; then
    echo "All pipelines completed successfully."
  else
    echo "Failed pipelines:"
    for f in "${pipeline_failures[@]}"; do
      echo "  $f"
      case "$f" in
        "browser-captures (prep)") echo "    → check ext/browser-captures/claude/ and Safari setup" ;;
        "chat-exports (prep)")   echo "    → populate ext/chat-exports/ with a bulk export (see PREP.sh --help)" ;;
        "code-projects (prep)")  echo "    → check ext/code-projects/ symlink setup" ;;
        *)                       echo "    → scroll up: the failing step prints its error and the path of its own log" ;;
      esac
    done
  fi
  # Any step that wants the reader to act prints a self-contained "→ run:" line;
  # gather them here so the tail — the only part anyone reads — carries every
  # suggested command. The log is safe to read mid-tee: those lines are long flushed.
  local suggestions
  suggestions="$(grep -F '→ run:' "$LOG_FILE" 2>/dev/null | sed 's/^.*→ run: /  /' | sort -u)" || true
  if [[ -n "$suggestions" ]]; then
    echo "Suggested commands (context beside each '→ run:' line above):"
    printf '%s\n' "$suggestions"
  fi
  echo "Run src/test/pre_commit.sh, then: git diff --cached src/test/pre_commit.log"
  echo "Log: $LOG_FILE"
}

mkdir -p "$(dirname "$LOG_FILE")"
main "$@" 2>&1 | tee "$LOG_FILE"
