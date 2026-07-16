#!/usr/bin/env bash
# pre_commit.sh (yoga check) — the three-tier check suite; also the pre-commit hook.
#
# Usage:
#   src/test/pre_commit.sh [--fix]    # --fix runs every fix command, stages with git add -u
#   ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit    # install (itself gated)
#
# Tiers: code + schema are deterministic on any clone (the committed log carries
# only these); data is machine-local, advisory. As the installed hook, failures
# veto only on the default branch; manual runs always exit non-zero on failure.
# Idempotence violations and a run that could not execute block on every branch.
# Read a failure via: git diff --cached src/test/pre_commit.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

parse_args() {
  case "${1:-}" in
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  esac
}

# The remote's default branch, read from origin/HEAD (recorded at clone time;
# refresh with: git remote set-head origin -a). Falls back to 'main' when unset
# (e.g. a fresh git init with no remote).
default_branch() {
  git -C "$REPO_DIR" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null \
    | sed 's|^origin/||' | grep . || echo main
}

# Is .git/hooks/pre-commit the load-bearing symlink to this script? Resolved
# via --git-path so a worktree checkout probes the right hooks directory.
hook_installed() {
  local hook link dir
  hook="$(git -C "$REPO_DIR" rev-parse --git-path hooks/pre-commit 2>/dev/null)" || return 1
  [[ "$hook" = /* ]] || hook="$REPO_DIR/$hook"
  [[ -L "$hook" ]] || return 1
  link="$(readlink "$hook")"
  [[ "$link" = /* ]] || link="$(dirname "$hook")/$link"
  dir="$(cd "$(dirname "$link")" 2>/dev/null && pwd)" || return 1
  [[ "$dir/$(basename "$link")" == "$REPO_DIR/src/test/pre_commit.sh" ]]
}

# Epoch mtime, BSD then GNU stat (a Linux clone must not silently lose the
# did-the-checks-run probe); 0 on a missing file.
_mtime() {
  stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0
}

main() {
  parse_args "$@"

  mkdir -p "$REPO_DIR/cache"

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
  before="$(_mtime "$REPO_DIR/src/test/pre_commit.log")"
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" || rc=$?
  after="$(_mtime "$REPO_DIR/src/test/pre_commit.log")"

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

  # The installation gate (see header). After the checks, so a failing run is
  # still a full report; before the branch-advisory verdict, so it is weighed
  # like any other failure.
  if ! hook_installed; then
    echo "✗ pre_commit is not installed as the git pre-commit hook — nothing vets a commit until it is:"
    echo "    ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit"
    if [[ $rc -eq 0 ]]; then rc=1; fi
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
