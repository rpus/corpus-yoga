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
#   ./RUNME.sh                        # all pipelines
#   ./RUNME.sh --pay-for-inference    # also run infer_tables.sh for chat-exports (costs money)
#
# After running, check results with:
#   src/test/pre_commit.sh            # full check suite; read via: git diff src/test/pre_commit.log

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${VENV:=$HOME/venvs/general}"

parse_args() {
  pay_for_inference=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --pay-for-inference) pay_for_inference="--pay-for-inference"; shift ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Usage: $0 [--pay-for-inference]"; echo "Pass --help for more information."; exit 1 ;;
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
  pip install -q -r "$SCRIPT_DIR/src/requirements.txt"
}

prep_pipeline() {
  local name="$1"; shift
  echo "── prep: ${name} ────────────────────────────────────────────────────────────"
  "$SCRIPT_DIR/src/main/${name}/PREP.sh" "$@"
  echo ""
}

run_pipeline() {
  local name="$1"; shift
  echo "── ${name} ──────────────────────────────────────────────────────────────────"
  "$SCRIPT_DIR/src/main/${name}/RUNME.sh" "--${name}" "$SCRIPT_DIR/ext/${name}" "$@"
  echo ""
}

main() {
  parse_args "$@"
  basename "$0"

  require_cmd jq "install via: brew install jq"
  local python; python="$(find_python3)"
  ensure_venv "$python"
  install_deps

  mkdir -p "$SCRIPT_DIR/ext"

  prep_pipeline browser-captures
  run_pipeline browser-captures

  prep_pipeline chat-exports
  run_pipeline chat-exports ${pay_for_inference:+"$pay_for_inference"}

  prep_pipeline code-projects
  run_pipeline code-projects

  echo "── done ──────────────────────────────────────────────────────────────────────"
  echo "Run src/test/pre_commit.sh, then: git diff src/test/pre_commit.log"
}

main "$@"
