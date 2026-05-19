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
