#!/usr/bin/env bash
# run.sh (yoga test run) — the three-tier check suite; also the pre-commit hook.
#
# Usage:
#   src/test/run.sh [--fix]    # --fix runs every fix command; stages nothing
#   yoga test install-hook                        # install as the hook
#
# ONE behaviour, however it is called: it asks neither what it was invoked as nor
# which branch you are on. A failure exits non-zero — as `yoga test run`, as the hook,
# on trunk, on a branch, detached. Deliberate WIP is `git commit --no-verify`, said
# out loud, not inferred from your branch name.
#
# It NEVER touches your index. `git add` cannot be undone — it cannot tell "the tool
# staged this" from "this was already staged, differently", so staging over a
# `git add -p` hunk destroys it with nothing to restore from. The artifacts it rewrites
# (run.log, xref.csv) are yours to stage; stale, it refuses and says so.
#
# Tiers: code + schema are deterministic on any clone (the committed log carries
# only these); data is machine-local, advisory. Whether the hook is installed is a
# machine-local fact that `yoga prerequisites` reports as an ERROR; a hook that RUNS
# while being the outdated form is refused below, since only a running hook can say so.
# Read a failure:
# git diff rsc/test/run.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Gate the COMMITTING TREE, not this script's home. Worktrees share the main
# checkout's hooks, and the hook symlink resolves HERE — so before this guard,
# a worktree commit ran the main checkout's gate against the main checkout's
# files inside the WORKTREE's git context (GIT_DIR env): a chimera that
# regenerated one tree's artifacts, diffed them against another tree's index,
# and refused with a demand no staging could satisfy, leaving --no-verify as the
# only way out. Re-exec the committing tree's OWN
# vintage of this script: each tree self-gates. THE RULE, for hook and hand
# alike: the COMMITTING TREE WINS — the gate follows the git context
# (rev-parse), never the script's home, so even a manual cross-tree
# invocation gates the tree you stand in: the only tree your git context
# could be about to commit. Manual runs from this repo are unaffected
# (toplevel == this repo). prepare_commit_msg stays home-anchored on purpose:
# the machine binding it reads is machine-scoped and absent from worktrees.
TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -n "$TOPLEVEL" && "$TOPLEVEL" != "$REPO_DIR" ]]; then
  if [[ -x "$TOPLEVEL/src/test/run.sh" ]]; then
    exec "$TOPLEVEL/src/test/run.sh" "$@"
  fi
  # REFUSE, never fall through (PR #25 review): running the home gate against
  # the home tree inside the other tree's git context is exactly the chimera
  # this guard abolishes — a fallthrough would restore it silently, with the
  # same unsatisfiable ERROR that cost a day. A loud refusal is recoverable.
  echo "ERROR: cannot gate $TOPLEVEL — no executable src/test/run.sh there." >&2
  echo "       Restore that tree's gate (or commit from a tree that has one);" >&2
  echo "       this home gate will not gate a different tree." >&2
  exit 1
fi

# Running AS the pre-commit hook (git exports GIT_INDEX_FILE to it). An OUTDATED hook —
# a symlink to this file, or a copy of it — still runs, and is exactly the form that
# dangles in silence when this file is renamed: git skips a hook it cannot resolve and
# says nothing, so the gate fails OPEN. While such a hook is in place, refuse. The only
# thing still executing is the one that can say so, and the remedy is one command.
#
# The test is EQUALITY with src/test/pre-commit-hook.sh, the one authority on what an
# installed hook is — not a pattern, which a longer or conditional hook would satisfy
# while doing something else entirely. `yoga prerequisites` asks the same question of the
# same file.
if [[ -n "${GIT_INDEX_FILE:-}" ]]; then
  hook_path="$(git -C "$REPO_DIR" rev-parse --git-path hooks/pre-commit 2>/dev/null || true)"
  [[ -z "$hook_path" || "$hook_path" = /* ]] || hook_path="$REPO_DIR/$hook_path"
  if [[ -n "$hook_path" ]] && ! cmp -s "$hook_path" "$REPO_DIR/src/test/pre-commit-hook.sh"; then
    echo "ERROR: this commit ran an OUTDATED pre-commit hook." >&2
    echo "       It points at a file rather than naming \`yoga test run\`, so renaming that" >&2
    echo "       file would disarm the gate in silence. Nothing is wrong with the change." >&2
    echo "       → run: yoga test install-hook" >&2
    exit 1
  fi
fi

# The artifacts run.py rewrites on every run — the idempotence subject.
ARTIFACTS=(rsc/test/run.log rsc/test/xref.csv)

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

  # Run once — run.py writes its own report artifacts: the COMMITTED
  # rsc/test/run.log (code+schema only, byte-identical on any clone — the
  # machine-local data tier never enters a committed file) plus the full report
  # to tmp/logs/test/run.log; only the tail (score + WARN + verdict) prints
  # to the terminal here. This run's status is unused (a failing report is still a
  # report; the exit verdict comes from the second run) — || true, for exactly that.
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/run.py" "$@" || true

  # Copy the first run's artifacts aside. Staging them and diffing the worktree
  # against the index would make a QUESTION mutate the index to answer itself. The
  # claim is only ever "run 1 and run 2 agree", so compare the two runs directly and
  # leave git out of it.
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
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/run.py" >/dev/null || rc=$?

  # --fix changed the world between the two writes: a failing first run and a
  # clean second one is the fixes WORKING, not an idempotence violation.
  if [[ $fix_mode -eq 0 ]]; then
    for a in "${ARTIFACTS[@]}"; do
      if ! diff -q "$snap/$(basename "$a")" "$REPO_DIR/$a" >/dev/null 2>&1; then
        echo "ERROR: the check suite is not idempotent — $a changed on the second run." >&2
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
