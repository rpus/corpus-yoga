#!/usr/bin/env bash
# export.sh (corpus-yoga export) — the bulk export: manifests and their captured payloads.
#
# Usage:
#   corpus-yoga export                                  # status: manifests held, payloads captured
#   corpus-yoga export capture [--manifest <file>] [--to <dir>]

set -euo pipefail

SELF='src/main/cli/export/export.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_DIR/src/main/cli/parse_argv.sh"

STORE="$REPO_DIR/data/input/claude/chat/bulk-export"

# rows mirror the store: one line per manifest (payload dir beside it or not),
# one per batch dir — a read face, no writes.
status() {
  if [[ ! -d "$STORE" ]]; then
    echo "export: no store at data/input/claude/chat/bulk-export — nothing deposited"
    return 0
  fi
  local store_rel="${STORE#"$REPO_DIR/"}"
  local found=0 m stem batch d derived="" unfetched=()
  for m in "$STORE"/manifest-*.json; do
    [[ -e "$m" ]] || continue
    found=1; stem="$(basename "$m" .json)"
    # the same derivation capture.py performs: the prefix swapped, the star kept whole
    batch="data-${stem#manifest-}"
    derived="$derived $batch"
    if [[ -d "$STORE/$batch" ]]; then
      echo "  $(basename "$m"): payload held in $batch/"
    else
      unfetched+=("$(basename "$m")")
    fi
  done
  for d in "$STORE"/data-*/; do
    [[ -d "$d" ]] || continue
    found=1
    case " $derived " in *" $(basename "$d") "*) continue ;; esac
    echo "  export $(basename "$d"): no manifest held for it (the pre-manifest vintage, or its manifest disposed)"
  done
  if (( ${#unfetched[@]} )); then
    echo "  ${#unfetched[@]} unfetched; to fetch:"
    local f
    for f in "${unfetched[@]}"; do
      echo "    → run: ./corpus-yoga export capture --manifest $store_rel/$f"
    done
  fi
  [[ "$found" == 1 ]] || echo "export: store empty — request one at https://claude.ai/settings/data-privacy-controls, deposit the emailed manifest here"
}

case "${1-}" in
  '')        status ;;
  capture)   shift; parse_argv export capture "$@"; exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/export/capture.py" "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "corpus-yoga export: unknown argument: $1 (try: corpus-yoga export --help)" >&2; exit 1 ;;
esac
