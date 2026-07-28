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
# pre-commit names the COMMAND, not the file behind it. A symlink to an implementation
# dangles the moment that file is renamed, and git treats a hook it cannot resolve as no
# hook at all — silently, so the gate fails OPEN and every commit lands unchecked until
# someone runs `yoga prerequisites`. `yoga test run` is the name; which file serves it is
# the CLI's business (#46: what you are told to run is a command, never a repo script by
# path). A shim of one line cannot drift the way a copied script would: its content is an
# invocation, and that the invocation resolves is what the declaration tree already holds.
#
# prepare-commit-msg stays a SYMLINK, home-anchored. It reads the machine binding, which
# is machine-scoped and absent from worktrees, so it must NOT follow the committing tree
# the way `git rev-parse --show-toplevel` would make it.
#
# Both, always: they are the same machinery on the same event, and installing one without
# the other has no reason (G21 — naming which would flag an axis the command already is).
install_hook() {
  local git_dir
  git_dir="$(git -C "$REPO_DIR" rev-parse --git-path hooks)" || {
    echo "yoga test install-hook: not a git checkout" >&2; exit 1; }
  mkdir -p "$git_dir"

  # UNLINK first. Every clone installed before this carries a symlink here, and `>`
  # FOLLOWS a symlink: redirecting onto it would write the shim through the link and
  # destroy src/test/run.sh, on exactly the machines that are upgrading.
  rm -f "$git_dir/pre-commit"
  # shellcheck disable=SC2016  # the shim resolves its own toplevel AT COMMIT TIME, in the
  # committing tree — expanding it here would nail the hook to this checkout
  printf '%s\n' '#!/usr/bin/env bash' \
    '# yoga test install-hook wrote this. It names the COMMAND: a symlink to an' \
    '# implementation dangles when that file is renamed, and git skips an unresolvable' \
    '# hook without a word.' \
    'exec "$(git rev-parse --show-toplevel)/yoga" test run "$@"' > "$git_dir/pre-commit"
  chmod +x "$git_dir/pre-commit"
  echo "hook: $git_dir/pre-commit → yoga test run"

  ln -sfn "../../src/test/prepare_commit_msg.sh" "$git_dir/prepare-commit-msg"
  echo "hook: $git_dir/prepare-commit-msg → $(readlink "$git_dir/prepare-commit-msg")"

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
