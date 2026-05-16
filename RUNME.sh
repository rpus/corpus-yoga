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

pay_for_inference=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pay-for-inference) pay_for_inference="--pay-for-inference"; shift ;;
    --help|-h)
      grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
    *)
      echo "Unknown argument: $1"; echo "Usage: $0 [--pay-for-inference]"; exit 1 ;;
  esac
done

echo "── browser-captures ──────────────────────────────────────────────────────────"
"$SCRIPT_DIR/src/main/browser-captures/RUNME.sh" \
  --browser-captures "$SCRIPT_DIR/ext/browser-captures"

echo ""
echo "── chat-exports ──────────────────────────────────────────────────────────────"
# shellcheck disable=SC2086
"$SCRIPT_DIR/src/main/chat-exports/RUNME.sh" \
  --chat-exports "$SCRIPT_DIR/ext/chat-exports" \
  $pay_for_inference

echo ""
echo "── code-projects ─────────────────────────────────────────────────────────────"
"$SCRIPT_DIR/src/main/code-projects/RUNME.sh" \
  --code-projects "$SCRIPT_DIR/ext/code-projects"

echo ""
echo "── done ──────────────────────────────────────────────────────────────────────"
echo "Run src/test/pre_commit.sh, then: git diff src/test/pre_commit.log"
