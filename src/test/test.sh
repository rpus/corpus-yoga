#!/usr/bin/env bash
# test.sh (yoga test) — the checks over this repo, and the hook that runs them.
#
# Usage:
#   yoga test              # status: which checks exist, and whether the hook is installed
#   yoga test run [--fix]  # the three-tier suite (also what the pre-commit hook runs)
#   yoga test xref         # rebuild the cross-reference table, write it, and report
#   yoga test install-hook # point .git/hooks/pre-commit at run.sh — idempotent
#
# The slot after `test` holds WHICH check, not a verb: `run` is the whole suite, `xref`
# is one of them. That is why `yoga xref check` retired — `check` meant "reports, writes
# nothing" on supersede and "rebuild the table and write it" here, one word for opposite
# effects on the tree (#49).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# The hook is a SYMLINK, never a copy: a copy drifts silently from the file it was
# copied from, and nothing would report the divergence. Idempotent by construction —
# `ln -sfn` replaces whatever is there, including a dangling link left by a rename.
install_hook() {
  local hook
  hook="$(git -C "$REPO_DIR" rev-parse --git-path hooks/pre-commit)" || {
    echo "yoga test install-hook: not a git checkout" >&2; exit 1; }
  mkdir -p "$(dirname "$hook")"
  ln -sfn ../../src/test/run.sh "$hook"
  echo "hook: $(git -C "$REPO_DIR" rev-parse --git-path hooks/pre-commit) → $(readlink "$hook")"
  echo "  every commit now runs yoga test run; deliberate WIP is git commit --no-verify"
}

status() {
  echo "checks: src/test/run.py — $(grep -c '^def check_' "$SCRIPT_DIR/run.py") check sections"
  echo "  expectation: rsc/test/run_expected_checks · report: rsc/test/run.log · xrefs: rsc/test/xref.csv"
  local hook
  if hook="$(git -C "$REPO_DIR" rev-parse --git-path hooks/pre-commit 2>/dev/null)" && [[ -L "$hook" ]]; then
    echo "  hook: installed → $(readlink "$hook")"
  else
    echo "  hook: not installed — yoga test install-hook"
  fi
}

case "${1-}" in
  '')           status ;;
  run)          shift; exec "$SCRIPT_DIR/run.sh" "$@" ;;
  xref)         shift; exec "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/xref.py" "$@" ;;
  install-hook) shift; install_hook "$@" ;;
  --help|-h)    awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  *) echo "Usage: yoga test [run [--fix] | xref | install-hook]  (yoga test -h for details)" >&2; exit 1 ;;
esac
