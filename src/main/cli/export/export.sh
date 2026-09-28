#!/usr/bin/env bash
# export.sh (corpus-yoga export) — the bulk export: manifests and their captured payloads.
#
# Usage:
#   corpus-yoga export                                  # status: the manifests and payloads held and staged
#   corpus-yoga export capture --manifest <file> [--to <dir>]   # the manifest where the download left it
#   corpus-yoga export promote [--rehearsal <stamp>]    # what capture staged, into data/input, judged by that rehearsal (default: the newest)

set -euo pipefail

SELF='src/main/cli/export/export.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_DIR/src/main/tier.sh"
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_DIR/src/main/cli/parse_argv.sh"

STORE="$DATA_DIR/input/claude/chat/bulk-export"
STAGE="$TMP_STAGE/input/claude/chat/bulk-export"

# one line per manifest of a root, then one per data-* directory no manifest there names
manifests() {
  local root="$1" state="$2" m stem batch d derived=""
  [[ -d "$root" ]] || return 0
  for m in "$root"/manifest-*.json; do
    [[ -e "$m" ]] || continue
    stem="$(basename "$m" .json)"
    # the same derivation capture.py performs: the prefix swapped, the star kept whole
    batch="data-${stem#manifest-}"
    derived="$derived $batch"
    if [[ -d "$root/$batch" ]]; then
      echo "  $state: $(basename "$m") with $batch/ - its one-use URLs spent"
    else
      echo "  $state: $(basename "$m") without $batch/ - unfetched:"
      echo "    → run: corpus-yoga export capture --manifest ${m#"$TIER_REPO/"}"
    fi
  done
  for d in "$root"/data-*/; do
    [[ -d "$d" ]] || continue
    case " $derived " in *" $(basename "$d") "*) continue ;; esac
    echo "  $state: $(basename "$d")/ without a manifest"
  done
}

# a read face, no writes: what shared storage holds, then what the stage holds
status() {
  local lines
  lines="$(manifests "$STORE" held; manifests "$STAGE" staged)"
  if [[ -z "$lines" ]]; then
    echo "export: nothing held or staged - request an export at https://claude.ai/settings/data-privacy-controls, then corpus-yoga export capture --manifest <the downloaded manifest>"
    return 0
  fi
  echo "export: ${STORE#"$TIER_REPO/"} (held), ${STAGE#"$TIER_REPO/"} (staged)"
  echo "$lines"
}

case "${1-}" in
  '')        status; "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/corpus.py" report export ;;
  capture)   shift; parse_argv export capture "$@"; exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/export/capture.py" "$@" ;;
  promote)   shift; parse_argv export promote "$@"; exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/corpus.py" promote export "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "corpus-yoga export: unknown argument: $1 (try: corpus-yoga export --help)" >&2; exit 1 ;;
esac
