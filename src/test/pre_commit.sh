#!/usr/bin/env bash
# Pre-commit hook wrapper. Install with:
#   ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit
#
# Usage:
#   src/test/pre_commit.sh
#   src/test/pre_commit.sh --fix   # run all fix commands and stage with git add -u
#
# Strictness is branch-aware IN HOOK CONTEXT ONLY (invoked as 'pre-commit' via the
# symlink): check failures veto a commit only on the default branch — a feature
# branch may commit work-in-progress, its PR review is the gate that matters.
# Manual runs ('pre_commit.sh') always exit non-zero on failure, so scripts and CI
# read an honest status. The idempotence check blocks everywhere: an unstable
# committed log would churn on every subsequent commit, whatever the branch.
# (Capturing rc instead of dying at the first run also means a failing run still
# stages its regenerated artifacts and still gets idempotence-checked.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

parse_args() {
  case "${1:-}" in
    --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
  esac
}

# The remote's default branch, read from origin/HEAD (recorded at clone time;
# refresh with: git remote set-head origin -a). Falls back to 'main' when unset
# (e.g. a fresh git init with no remote).
default_branch() {
  git -C "$REPO_DIR" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null \
    | sed 's|^origin/||' | grep . || echo main
}

main() {
  parse_args "$@"

  mkdir -p "$REPO_DIR/gen"

  local strict=1 branch trunk
  if [[ "$(basename "$0")" == "pre-commit" ]]; then
    trunk="$(default_branch)"
    branch="$(git -C "$REPO_DIR" branch --show-current)"
    [[ "$branch" == "$trunk" ]] || strict=0
  fi

  # Run once — pre_commit.py writes its own report artifacts: the COMMITTED
  # src/test/pre_commit.log (code+schema only, byte-identical on any clone — the
  # machine-local data tier never enters a committed file) plus the full report
  # to logs/src/test/pre_commit.log; the full report also prints here.
  local rc=0
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" "$@" || rc=$?

  # Stage the generated artifacts so the second run sees a clean baseline.
  git -C "$REPO_DIR" add src/test/pre_commit.log src/test/xref.csv

  # Run again — must produce no further changes.
  rc=0
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" || rc=$?
  if ! git -C "$REPO_DIR" diff --quiet src/test/pre_commit.log src/test/xref.csv; then
    echo 'ERROR: pre_commit is not idempotent — pre_commit.log or xref.csv changed on second run.' >&2
    git -C "$REPO_DIR" diff src/test/pre_commit.log src/test/xref.csv >&2
    exit 1
  fi

  if [[ $rc -ne 0 && $strict -eq 0 ]]; then
    echo "pre-commit: checks failed, but '$branch' is not '$trunk' — advisory here; commit allowed"
    rc=0
  fi
  exit $rc
}

main "$@"
