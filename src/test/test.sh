#!/usr/bin/env bash
# test.sh (yoga test) — the checks over this repo, and the hook that runs them.
#
# Usage:
#   yoga test              # status: which checks exist, and whether the hook is installed
#   yoga test run [--fix]  # the three-tier suite (also what the pre-commit hook runs)
#   yoga test xref         # rebuild the cross-reference table, write it, and report
#   yoga test install-hook # point .git/hooks at run.sh and prepare_commit_msg.sh
#
# The slot after `test` holds WHICH check, not a verb: `run` is the whole suite, `xref`
# is one of them. That is why `yoga xref check` retired — `check` meant "reports, writes
# nothing" on supersede and "rebuild the table and write it" here, one word for opposite
# effects on the tree (#49).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# BOTH hooks this repo owns, because installing one without the other has no reason:
# they are the same machinery (src/test/), on the same event, and `yoga prerequisites`
# nags for both. Naming which to install would put a flag on an axis the command already
# is (G21), and the answer would always be "both".
#
# A SYMLINK, never a copy: a copy drifts silently from the file it was copied from, and
# nothing would report the divergence. Idempotent by construction — `ln -sfn` replaces
# whatever is there, including a dangling link left by a rename.
install_hook() {
  local git_dir
  git_dir="$(git -C "$REPO_DIR" rev-parse --git-path hooks)" || {
    echo "yoga test install-hook: not a git checkout" >&2; exit 1; }
  mkdir -p "$git_dir"
  local pair
  for pair in "pre-commit:run.sh" "prepare-commit-msg:prepare_commit_msg.sh"; do
    local event="${pair%%:*}" script="${pair##*:}"
    ln -sfn "../../src/test/$script" "$git_dir/$event"
    echo "hook: $git_dir/$event → $(readlink "$git_dir/$event")"
  done
  echo "  every commit now runs yoga test run and is stamped with its Signature;"
  echo "  deliberate WIP is git commit --no-verify"
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
