#!/usr/bin/env bash
# test.sh (corpus-yoga test) — the checks over this repo, and the hook that runs them.
#
# Usage:
#   corpus-yoga test              # status: which checks exist, and whether the hook is installed
#   corpus-yoga test run [--fix] [--fresh]  # the three-tier suite (--fresh ignores the section cache)
#   corpus-yoga test xref         # rebuild the cross-reference table, write it, and report
#   corpus-yoga test install-hook # point .git/hooks at run.sh and the prepare-commit-msg hook
#
# The slot after `test` holds WHICH check, not a verb: `run` is the whole suite, `xref`
# is one of them. That is why `corpus-yoga xref check` retired — `check` meant "reports, writes
# nothing" on supersede and "rebuild the table and write it" here, one word for opposite
# effects on the tree (#49).

set -euo pipefail

SELF='src/main/cli/test/test.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_DIR/src/main/cli/parse_argv.sh"

# BOTH hooks this repo owns, because installing one without the other has no reason:
# they are the same machinery (src/test/), on the same event, and `corpus-yoga prerequisites`
# nags for both. Naming which to install would put a flag on an axis the command already
# is (G21), and the answer would always be "both".
#
# pre-commit is a COPY of rsc/test/pre-commit-hook.sh, which is the one authority on what
# an installed hook must be: install writes it, prerequisites and the gate compare against
# it. A copy that drifts is caught by that comparison rather than trusted — the objection
# to copies is silent drift, and nothing here is silent.
#
# prepare-commit-msg stays a SYMLINK, home-anchored. It reads the machine binding, which
# is machine-scoped and absent from worktrees, so it must NOT follow the committing tree.
#
# Both, always: they are the same machinery on the same event, and installing one without
# the other has no reason (G21 — naming which would flag an axis the command already is).
install_hook() {
  local git_dir
  git_dir="$(git -C "$REPO_DIR" rev-parse --git-path hooks)" || {
    echo "corpus-yoga test install-hook: not a git checkout" >&2; exit 1; }
  mkdir -p "$git_dir"

  # UNLINK first: every clone installed before this carries a symlink here, and `cp`
  # FOLLOWS a symlink — copying onto it would write through the link and destroy the file
  # it points at, on exactly the machines that are upgrading.
  rm -f "$git_dir/pre-commit"
  cp "$REPO_DIR/rsc/test/pre-commit-hook.sh" "$git_dir/pre-commit"
  chmod +x "$git_dir/pre-commit"
  echo "hook: $git_dir/pre-commit ← rsc/test/pre-commit-hook.sh"

  ln -sfn "../../rsc/test/prepare-commit-msg-hook.sh" "$git_dir/prepare-commit-msg"
  echo "hook: $git_dir/prepare-commit-msg → $(readlink "$git_dir/prepare-commit-msg")"

  echo "  every commit now runs corpus-yoga test run and is stamped with its Signature;"
  echo "  deliberate WIP is git commit --no-verify"
}

status() {
  echo "checks: src/test/dev/run.py — $(grep -c '^def check_' "$REPO_DIR/src/test/dev/run.py") check sections"
  echo "  expectation: rsc/test/run_expected_checks · report: rsc/test/run.log · xrefs: rsc/test/xref.csv"
  local hook
  if hook="$(git -C "$REPO_DIR" rev-parse --git-path hooks/pre-commit 2>/dev/null)" && [[ -L "$hook" ]]; then
    echo "  hook: installed → $(readlink "$hook")"
  else
    echo "  hook: not installed — corpus-yoga test install-hook"
  fi
}

case "${1-}" in
  '')           status ;;
  run)          shift; parse_argv test run "$@"; exec "$REPO_DIR/src/test/dev/run.sh" "$@" ;;
  xref)         shift; parse_argv test xref "$@"; exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/dev/xref.py" "$@" ;;
  install-hook) shift; parse_argv test install-hook "$@"; install_hook "$@" ;;
  --help|-h)    awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  *) echo "Usage: corpus-yoga test [run [--fix] [--fresh] | xref | install-hook]  (corpus-yoga test -h for details)" >&2; exit 1 ;;
esac
