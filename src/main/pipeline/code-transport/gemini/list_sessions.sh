#!/usr/bin/env bash
# The sessions of one gemini project directory in the store, one source path per line:
# Antigravity's session is a directory, <project>/<session>/, holding its transcripts. Every
# directory is listed, as the declaration's glob counts it: one that holds no transcript
# is the conversion's to refuse, stated there, never passed over here.
#
# Usage:
#   src/main/pipeline/code-transport/gemini/list_sessions.sh <store>/<machine>/<project>
set -euo pipefail
SELF='src/main/pipeline/code-transport/gemini/list_sessions.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

for session in "${1%/}"/*/; do
  [[ -d "$session" ]] || continue
  echo "${session%/}"
done
