#!/usr/bin/env bash
# Pre-commit hook wrapper. Install with:
#   ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit
#
# Usage:
#   src/test/pre_commit.sh
#   src/test/pre_commit.sh --fix   # run all fix commands and stage with git add -u

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

  # Run once — pre_commit.py writes its own report artifacts: the COMMITTED
  # src/test/pre_commit.log (code+schema only, byte-identical on any clone — the
  # machine-local data tier never enters a committed file) plus the full report
  # to logs/src/test/pre_commit.log; the full report also prints here.
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" "$@"

  # Stage the generated artifacts so the second run sees a clean baseline.
  git -C "$REPO_DIR" add src/test/pre_commit.log src/test/xref.csv

  # Run again — must produce no further changes.
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py"
  if ! git -C "$REPO_DIR" diff --quiet src/test/pre_commit.log src/test/xref.csv; then
    echo 'ERROR: pre_commit is not idempotent — pre_commit.log or xref.csv changed on second run.' >&2
    git -C "$REPO_DIR" diff src/test/pre_commit.log src/test/xref.csv >&2
    exit 1
  fi
}

main "$@"
