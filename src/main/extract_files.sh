#!/usr/bin/env bash
# Run from the repo root, e.g.:
#   src/main/extract_files.sh --data-dir ../data-exports/data-2026-04-07-07-52-05-batch-0000
#   src/main/extract_files.sh --data-root ../data-exports

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen"

run_one() {
  local d="${1%/}"
  local name; name="$(basename "$d")"
  local log_path="$OUTPUT_DIR/$name/extracted_files/extract_files.log"
  mkdir -p "$(dirname "$log_path")"
  python "$SCRIPT_DIR/extract_files.py" --data-dir "$d" >> "$log_path" 2>&1
}

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
    echo "       $0 --data-root <path/to/data-exports>"
    exit 1
  fi

  # shellcheck source=/dev/null
  source ~/venvs/general/bin/activate

  if [[ -n "$data_dir" ]]; then
    run_one "$(cd "$data_dir" && pwd)"
  else
    for d in "$(cd "$data_root" && pwd)"/data-*/; do
      run_one "$d"
    done
  fi

  deactivate
}

main "$@"
