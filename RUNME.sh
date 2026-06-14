#!/usr/bin/env bash
# RUNME.sh — Process all Claude data exports.
#
# Runs three pipelines against their sibling input directories:
#
#   chat-exports     ext/chat-exports/      claude.ai bulk exports (conversations.json etc.)
#   code-projects    ext/code-projects/     Claude Code CLI sessions (~/.claude/projects/ symlink)
#   browser-captures ext/browser-captures/  Per-conversation live API JSON captures
#
# Each pipeline validates its inputs against all schema versions, then (for chat-exports)
# extracts files, infers tables, and renders a dashboard.
#
# Usage:
#   ./RUNME.sh                                      # all pipelines
#   ./RUNME.sh --browser-captures                   # also capture/update via Safari (slow)
#   ./RUNME.sh --pay-for-inference                  # also run infer_tables.sh for chat-exports (costs money)
#   ./RUNME.sh --browser-captures --pay-for-inference
#
# After running, check results with:
#   src/test/pre_commit.sh            # full check suite; read via: git diff src/test/pre_commit.log

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${VENV:=$HOME/venvs/general}"

parse_args() {
  pay_for_inference=""
  browser_captures=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --pay-for-inference) pay_for_inference="--pay-for-inference"; shift ;;
      --browser-captures) browser_captures="--discover";            shift ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Usage: $0 [--browser-captures] [--pay-for-inference]"; echo "Pass --help for more information."; exit 1 ;;
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

pipeline_runme_sh() {
  case "$1" in
    browser-captures) echo "src/main/browser-captures/claude/RUNME.sh" ;;
    *)                echo "src/main/$1/RUNME.sh" ;;
  esac
}
pipeline_ext_dir() {
  case "$1" in
    browser-captures) echo "ext/browser-captures/claude" ;;
    *)                echo "ext/$1" ;;
  esac
}

prep_pipeline() {
  local name="$1"; shift
  echo "── prep: ${name} ────────────────────────────────────────────────────────────"
  "$SCRIPT_DIR/src/main/${name}/PREP.sh" "$@"
  echo ""
}

run_pipeline() {
  local name="$1"; local script; script="$(pipeline_runme_sh "$name")"; local ext; ext="$(pipeline_ext_dir "$name")"; shift
  echo "── ${name} ──────────────────────────────────────────────────────────────────"
  "$SCRIPT_DIR/$script" "--${name}" "$SCRIPT_DIR/$ext" "$@"
  echo ""
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

  mkdir -p "$SCRIPT_DIR/ext"

  local -a pipeline_failures=()

  prep_pipeline_safe browser-captures ${browser_captures:+"$browser_captures"}
  run_pipeline_safe  browser-captures

  prep_pipeline_safe chat-exports
  run_pipeline_safe  chat-exports ${pay_for_inference:+"$pay_for_inference"}

  prep_pipeline_safe code-projects
  run_pipeline_safe  code-projects

  echo "── done $(date -u '+%Y-%m-%dT%H:%M:%SZ') ───────────────────────────────────────────"
  if [[ ${#pipeline_failures[@]} -eq 0 ]]; then
    echo "All pipelines completed successfully."
  else
    echo "Failed pipelines:"
    for f in "${pipeline_failures[@]}"; do
      echo "  $f"
      case "$f" in
        browser-captures)        echo "    → check gen/browser-captures/claude/*/validation/apiConversation/*.log" ;;
        "browser-captures (prep)") echo "    → check ext/browser-captures/claude/ and Safari setup" ;;
        chat-exports)            echo "    → check gen/chat-exports/*/validation/*.log" ;;
        "chat-exports (prep)")   echo "    → populate ext/chat-exports/ with a bulk export (see PREP.sh --help)" ;;
        code-projects)           echo "    → check gen/code-projects/*/validation/*.log" ;;
        "code-projects (prep)")  echo "    → check ext/code-projects/ symlink setup" ;;
      esac
    done
  fi
  echo "Run src/test/pre_commit.sh, then: git diff src/test/pre_commit.log"
  echo "Log: $LOG_FILE"
}

mkdir -p "$(dirname "$LOG_FILE")"
main "$@" 2>&1 | tee "$LOG_FILE"
