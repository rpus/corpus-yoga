#!/usr/bin/env bash
# export.sh (corpus-yoga export) — the bulk export: manifests and their captured payloads.
#
# Usage:
#   corpus-yoga export                                  # status: the manifests and payloads held and staged
#   corpus-yoga export capture --manifest <file>      # the manifest where the download left it
#   corpus-yoga export promote [--rehearsal <stamp>]    # what capture staged, into data/input, judged by that rehearsal (default: the newest)

set -euo pipefail

SELF='src/main/cli/export/export.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_DIR/src/main/cli/parse_argv.sh"

# a read face, no writes: the exports held and staged, each paired or unpaired
status() {
  local lines
  lines="$("$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/corpus.py" pairs export)"
  if [[ -z "$lines" ]]; then
    echo "export: nothing held or staged - request an export at https://claude.ai/settings/data-privacy-controls, then corpus-yoga export capture --manifest <the downloaded manifest>"
    return 0
  fi
  echo "export: a staged export <X> is data-<X>/ with manifest-<X>.json, its capture's record; shared storage holds data-<X>/"
  echo "$lines"
}

case "${1-}" in
  '')        status; "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/corpus.py" report export ;;
  capture)   shift; parse_argv export capture "$@"; exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/export/capture.py" "$@" ;;
  promote)   shift; parse_argv export promote "$@"; exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/corpus.py" promote export "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "corpus-yoga export: unknown argument: $1 (try: corpus-yoga export --help)" >&2; exit 1 ;;
esac
