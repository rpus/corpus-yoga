#!/usr/bin/env bash
# The sessions of one claude project directory in the store, one source path per line:
# Claude Code writes a session as <project>/<session>.jsonl.
#
# Usage:
#   src/main/agent/claude/list_sessions.sh <store>/<machine>/<project>
set -euo pipefail

for jsonl in "${1%/}"/*.jsonl; do
  [[ -f "$jsonl" ]] || continue
  echo "$jsonl"
done
