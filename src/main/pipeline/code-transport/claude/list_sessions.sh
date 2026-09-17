#!/usr/bin/env bash
# The sessions of one claude project directory in the store, one source path per line:
# Claude Code writes a session as <project>/<session>.jsonl.
#
# Usage:
#   src/main/pipeline/code-transport/claude/list_sessions.sh <store>/<machine>/<project>
set -euo pipefail
SELF='src/main/pipeline/code-transport/claude/list_sessions.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

for jsonl in "${1%/}"/*.jsonl; do
  [[ -f "$jsonl" ]] || continue
  echo "$jsonl"
done
