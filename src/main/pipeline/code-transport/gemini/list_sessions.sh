#!/usr/bin/env bash
# The sessions of one gemini project directory in the store, one source path per line:
# Antigravity's session is a directory, <project>/<session>/, holding its transcripts - and a
# directory holding none is no session yet: the store is carried by iCloud, which
# materialises a directory before its files, so one room can meet the other's fresh
# capture empty. Such a directory is stated on stderr and not listed, as claude's
# undelivered .jsonl is not; the declaration's glob selects the transcript, so the audit
# counts what is listed here and nothing else.
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
  if [[ ! -f "${session}transcript.jsonl" && ! -f "${session}transcript_full.jsonl" ]]; then
    echo "  ($(basename "$session"): holds no transcript yet - not a session; iCloud may still be delivering it)" >&2
    continue
  fi
  echo "${session%/}"
done
