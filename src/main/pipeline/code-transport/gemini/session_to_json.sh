#!/usr/bin/env bash
# Convert one captured Antigravity session to session.json, the gemini session family's
# datum: the untruncated transcript_full.jsonl where the capture holds it, else
# transcript.jsonl, one step per line become one array.
#
# Usage:
#   src/main/pipeline/code-transport/gemini/session_to_json.sh <session-dir> <output.json>
set -euo pipefail
SELF='src/main/pipeline/code-transport/gemini/session_to_json.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <session-dir> <output.json>"
  exit 1
fi
echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
"$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/transcript_to_json.py" "$1" "$2"
