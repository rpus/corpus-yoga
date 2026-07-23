#!/usr/bin/env bash
# pre_commit.sh (yoga check) — the three-tier check suite; also the pre-commit hook.
#
# Usage:
#   src/test/pre_commit.sh [--fix]    # --fix runs every fix command; stages nothing
#   ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit    # install
#
# ONE behaviour, however it is called: it asks neither what it was invoked as nor
# which branch you are on. A failure exits non-zero — as `yoga check`, as the hook,
# on trunk, on a branch, detached. Deliberate WIP is `git commit --no-verify`, said
# out loud, not inferred from your branch name.
#
# It NEVER touches your index. `git add` cannot be undone — it cannot tell "the tool
# staged this" from "this was already staged, differently", so staging over a
# `git add -p` hunk destroys it with nothing to restore from. The artifacts it rewrites
# (pre_commit.log, xref.csv) are yours to stage; stale, it refuses and says so.
#
# Tiers: code + schema are deterministic on any clone (the committed log carries
# only these); data is machine-local, advisory. Whether the hook is installed is a
# machine-local fact and `yoga prerequisites` is its one voice. Read a failure:
# git diff src/test/pre_commit.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Gate the COMMITTING TREE, not this script's home. Worktrees share the main
# checkout's hooks, and the hook symlink resolves HERE — so before this guard,
# a worktree commit ran the main checkout's gate against the main checkout's
# files inside the WORKTREE's git context (GIT_DIR env): a chimera that
# regenerated one tree's artifacts, diffed them against another tree's index,
# and refused with a demand no staging could satisfy (found 2026-07-23 by
# reading-room, committing a rehearsal record inside the recipe's worktree —
# their only route out was --no-verify). Re-exec the committing tree's OWN
# vintage of this script: each tree self-gates. THE RULE, for hook and hand
# alike: the COMMITTING TREE WINS — the gate follows the git context
# (rev-parse), never the script's home, so even a manual cross-tree
# invocation gates the tree you stand in: the only tree your git context
# could be about to commit. Manual runs from this repo are unaffected
# (toplevel == this repo). prepare_commit_msg stays home-anchored on purpose:
# the machine binding it reads is machine-scoped and absent from worktrees.
TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -n "$TOPLEVEL" && "$TOPLEVEL" != "$REPO_DIR" ]]; then
  if [[ -x "$TOPLEVEL/src/test/pre_commit.sh" ]]; then
    exec "$TOPLEVEL/src/test/pre_commit.sh" "$@"
  fi
  # REFUSE, never fall through (PR #25 review): running the home gate against
  # the home tree inside the other tree's git context is exactly the chimera
  # this guard abolishes — a fallthrough would restore it silently, with the
  # same unsatisfiable ERROR that cost a day. A loud refusal is recoverable.
  echo "ERROR: cannot gate $TOPLEVEL — no executable src/test/pre_commit.sh there." >&2
  echo "       Restore that tree's gate (or commit from a tree that has one);" >&2
  echo "       this home gate will not gate a different tree." >&2
  exit 1
fi

# The artifacts pre_commit.py rewrites on every run — the idempotence subject.
ARTIFACTS=(src/test/pre_commit.log src/test/xref.csv)

parse_args() {
  case "${1:-}" in
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"

  mkdir -p "$REPO_DIR/tmp/cache"

  local fix_mode=0
  if [[ "${1:-}" == "--fix" ]]; then fix_mode=1; fi

  # Run once — pre_commit.py writes its own report artifacts: the COMMITTED
  # src/test/pre_commit.log (code+schema only, byte-identical on any clone — the
  # machine-local data tier never enters a committed file) plus the full report
  # to tmp/logs/src/test/pre_commit.log; only the tail (score + WARN + verdict) prints
  # to the terminal here. This run's status is unused (a failing report is still a
  # report; the exit verdict comes from the second run) — || true, for exactly that.
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

  # Run again — must produce no further changes. Its report would just duplicate the
  # first run's on the terminal, so its stdout is discarded; only its exit code (the
  # verdict) and any stderr (a crash) matter here.
  local rc=0
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" >/dev/null || rc=$?

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

  # The artifacts' currency, guarded without touching anything. Deleting the old
  # `git add` deleted a guarantee along with the rudeness: it silently ensured
  # every commit carried freshly regenerated artifacts. Nothing reads the
  # COMMITTED log — check_score reads live counts — so a forgotten stage would
  # decay the byte-identical-on-any-clone contract one commit at a time, with no
  # check ever noticing. Refuse and tell; never stage on someone's behalf.
  # Worktree-vs-index is the right comparison: what is about to be committed must
  # be what a fresh run produces. Unchanged artifacts never diff, so this is
  # silent until it matters.
  if ! git -C "$REPO_DIR" diff --quiet -- "${ARTIFACTS[@]}" 2>/dev/null; then
    echo "ERROR: the regenerated artifacts are not staged — what would be committed is stale:" >&2
    printf '    → run: git add %s\n' "${ARTIFACTS[*]}" >&2
    rc=1
  fi

  exit $rc
}

main "$@"
