#!/usr/bin/env bash
# pre_commit.sh (yoga check) — the three-tier check suite; also the pre-commit hook.
#
# Usage:
#   src/test/pre_commit.sh [--fix]    # --fix runs every fix command; stages nothing
#   ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit    # install
#
# ONE behaviour, however it is called: it asks neither what it was invoked as nor
# which branch you are on. A failure exits non-zero — as `yoga check`, as the hook,
# on trunk, on a branch, detached. Deliberate work-in-progress is
# `git commit --no-verify`, said out loud, not inferred from your branch name.
#
# It NEVER touches your index. `git add` cannot be undone — it cannot tell "the tool
# staged this" from "this was already staged, differently", so staging over a hunk
# you staged with `git add -p` destroys it with nothing to restore from. The artifacts
# it rewrites (src/test/pre_commit.log, src/test/xref.csv) are yours to read and stage.
#
# Tiers: code + schema are deterministic on any clone (the committed log carries
# only these); data is machine-local, advisory. Whether the hook is installed is a
# machine-local fact and `yoga prerequisites` is its one voice.
# Read a failure: git diff src/test/pre_commit.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# The artifacts pre_commit.py rewrites on every run — the idempotence subject.
ARTIFACTS=(src/test/pre_commit.log src/test/xref.csv)

parse_args() {
  case "${1:-}" in
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"

  mkdir -p "$REPO_DIR/cache"

  local fix_mode=0
  if [[ "${1:-}" == "--fix" ]]; then fix_mode=1; fi

  # Run once — pre_commit.py writes its own report artifacts: the COMMITTED
  # src/test/pre_commit.log (code+schema only, byte-identical on any clone — the
  # machine-local data tier never enters a committed file) plus the full report
  # to logs/src/test/pre_commit.log; the full report also prints here. This run's
  # status is unused (a failing report is still a report; the exit verdict comes
  # from the second run) — || true, the idiom for exactly that.
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" "$@" || true

  # Copy the first run's artifacts aside. This used to stage them and diff the
  # worktree against the index, which made a QUESTION mutate your index to answer
  # itself. The claim is only ever "run 1 and run 2 agree", so compare the two
  # runs directly and leave git out of it.
  local snap; snap="$(mktemp -d)"
  trap 'rm -rf "$snap"' EXIT
  local a
  for a in "${ARTIFACTS[@]}"; do
    cp "$REPO_DIR/$a" "$snap/$(basename "$a")" 2>/dev/null || true
  done

  # Run again — must produce no further changes.
  local rc=0
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" || rc=$?

  # --fix changed the world between the two writes: a failing first run and a
  # clean second one is the fixes WORKING, not an idempotence violation.
  if [[ $fix_mode -eq 0 ]]; then
    for a in "${ARTIFACTS[@]}"; do
      if ! diff -q "$snap/$(basename "$a")" "$REPO_DIR/$a" >/dev/null 2>&1; then
        echo "ERROR: pre_commit is not idempotent — $a changed on the second run." >&2
        diff -u "$snap/$(basename "$a")" "$REPO_DIR/$a" >&2 || true
        exit 1
      fi
    done
  fi

  exit $rc
}

main "$@"
