#!/usr/bin/env bash
# Pre-commit hook wrapper. Install with:
#   ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit
#
# Usage:
#   src/test/pre_commit.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

parse_args() {
  case "${1:-}" in
    --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"

  mkdir -p "$REPO_DIR/gen"

  # Run once — generates pre_commit.log and xref.csv.
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" 2>&1 | tee "$REPO_DIR/src/test/pre_commit.log"

  # Stage the generated artifacts so the second run sees a clean baseline.
  git -C "$REPO_DIR" add src/test/pre_commit.log src/test/xref.csv

  # Run again — must produce no further changes.
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" 2>&1 | tee "$REPO_DIR/src/test/pre_commit.log"
  if ! git -C "$REPO_DIR" diff --quiet src/test/pre_commit.log src/test/xref.csv; then
    echo 'ERROR: pre_commit is not idempotent — pre_commit.log or xref.csv changed on second run.' >&2
    git -C "$REPO_DIR" diff src/test/pre_commit.log src/test/xref.csv >&2
    exit 1
  fi
}

main "$@"
