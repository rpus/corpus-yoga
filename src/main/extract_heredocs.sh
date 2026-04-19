#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   src/main/extract_heredocs.sh --data-dir ../exported-data/data-2026-04-07-07-52-05-batch-0000
#   src/main/extract_heredocs.sh --data-root ../exported-data

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

main() {
  local data_dir="" data_root=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --data-dir)  data_dir="$2";  shift 2 ;;
      --data-root) data_root="$2"; shift 2 ;;
      *) echo "Unknown argument: $1"
         echo "Usage: $0 --data-dir <path> | --data-root <path>"
         exit 1 ;;
    esac
  done

  if [[ -z "$data_dir" && -z "$data_root" ]]; then
    echo "Usage: $0 --data-dir <path/to/data-directory>"
    echo "       $0 --data-root <path/to/exported-data>"
    exit 1
  fi

  source ~/venvs/general/bin/activate

  if [[ -n "$data_dir" ]]; then
    python "$SCRIPT_DIR/extract_heredocs.py" --data-dir "$(cd "$data_dir" && pwd)"
  else
    for d in "$(cd "$data_root" && pwd)"/data-*/; do
      python "$SCRIPT_DIR/extract_heredocs.py" --data-dir "$d"
    done
  fi

  deactivate
}

main "$@"
