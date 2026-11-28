#!/usr/bin/env bash
# export.sh (corpus-yoga export) — the bulk export: manifests and their captured payloads.
#
# Usage:
#   corpus-yoga export                                  # status: the manifests and payloads held and staged
#   corpus-yoga export capture --manifest <file>      # the manifest where the download left it
#   corpus-yoga export promote    # what capture staged, into data/input, judged by the rehearsal record

set -euo pipefail

REPO_DIR="${CORPUS_YOGA_ROOT:?the repository root, which corpus-yoga hands every run it starts}"
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_DIR/src/main/cli/parse_argv.sh"

case "${1-}" in
  '')        exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/export/status.py" ;;   # a read face, no writes
  capture)   shift; parse_argv export capture "$@"; exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/export/capture.py" "$@" ;;
  promote)   shift; parse_argv export promote "$@"; exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/corpus.py" promote export "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "corpus-yoga export: unknown argument: $1 (try: corpus-yoga export --help)" >&2; exit 1 ;;
esac
