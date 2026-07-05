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
# read an honest status. Two things block on EVERY branch: the idempotence check
# (an unstable committed log would churn on every subsequent commit) and a run
# that could not execute at all (nothing verified — nothing to be advisory about).
# (Surviving a failing run instead of dying at it also means the run still stages
# its regenerated artifacts and still gets idempotence-checked.)

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

  local fix_mode=0
  if [[ "${1:-}" == "--fix" ]]; then fix_mode=1; fi

  local strict=1 branch trunk
  if [[ "$(basename "$0")" == "pre-commit" ]]; then
    trunk="$(default_branch)"
    branch="$(git -C "$REPO_DIR" branch --show-current)"
    # Detached HEAD reports an empty branch — stay strict: an amend or a rebase
    # stop on trunk history is exactly a commit this veto exists for.
    if [[ -n "$branch" && "$branch" != "$trunk" ]]; then strict=0; fi
  fi

  # Run once — pre_commit.py writes its own report artifacts: the COMMITTED
  # src/test/pre_commit.log (code+schema only, byte-identical on any clone — the
  # machine-local data tier never enters a committed file) plus the full report
  # to logs/src/test/pre_commit.log; the full report also prints here. This run's
  # status is unused (a failing report is still a report; the exit verdict comes
  # from the second run) — || true, the idiom for exactly that.
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" "$@" || true

  # Stage the generated artifacts so the second run sees a clean baseline.
  git -C "$REPO_DIR" add src/test/pre_commit.log src/test/xref.csv

  # Run again — must produce no further changes. The log's mtime doubles as the
  # did-the-checks-even-run probe for the advisory decision below.
  local before after rc=0
  before="$(stat -f %m "$REPO_DIR/src/test/pre_commit.log" 2>/dev/null || echo 0)"
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" || rc=$?
  after="$(stat -f %m "$REPO_DIR/src/test/pre_commit.log" 2>/dev/null || echo 0)"

  if [[ $fix_mode -eq 1 ]]; then
    # --fix changed the world between the two writes: a failing first log and a
    # clean second one is the fixes WORKING, not an idempotence violation. The
    # post-fix artifacts are the baseline; re-stage them (pre_commit.py already
    # told the operator to re-run pre_commit.sh to verify).
    git -C "$REPO_DIR" add src/test/pre_commit.log src/test/xref.csv
  elif ! git -C "$REPO_DIR" diff --quiet src/test/pre_commit.log src/test/xref.csv; then
    echo 'ERROR: pre_commit is not idempotent — pre_commit.log or xref.csv changed on second run.' >&2
    git -C "$REPO_DIR" diff src/test/pre_commit.log src/test/xref.csv >&2
    exit 1
  fi

  if [[ $rc -ne 0 && $strict -eq 0 ]]; then
    if [[ $rc -ge 126 || "$after" == "$before" ]]; then
      # 126/127-class exits and an untouched log both mean the checks could not
      # RUN (broken venv, crashed interpreter) — nothing was verified, so there
      # is nothing to be advisory about. Block on every branch.
      echo "pre-commit: checks could not run (exit $rc) — blocking on every branch" >&2
      exit $rc
    fi
    echo "pre-commit: checks failed, but '$branch' is not '$trunk' — advisory here; commit allowed"
    rc=0
  fi
  exit $rc
}

main "$@"
