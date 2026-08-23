#!/usr/bin/env bash
# run.sh (corpus-yoga test run) — the three-tier check suite; also the pre-commit hook.
#
# Usage:
#   src/test/dev/run.sh [--fix]    # --fix runs every fix command; stages nothing
#   src/test/dev/run.sh --fresh     # ignore the section cache: re-run every check
#   corpus-yoga test install-hook                        # install as the hook
#
# ONE behaviour, however it is called: it asks neither what it was invoked as nor
# which branch you are on. A failure exits non-zero — as `corpus-yoga test run`, as the hook,
# on trunk, on a branch, detached. Deliberate WIP is `git commit --no-verify`, said
# out loud, not inferred from your branch name.
#
# It NEVER touches your index. `git add` cannot be undone — it cannot tell "the tool
# staged this" from "this was already staged, differently", so staging over a
# `git add -p` hunk destroys it with nothing to restore from. The artifacts it rewrites
# (run.log, xref.csv) are yours to stage; stale, it refuses and says so.
#
# Sections replay from tmp/cache/test/ when their declared SUBJECT (the files they
# read) is stat-unchanged (#68). run.py checks (tree -> results; a check writes no
# artifacts), then renders every surface — the committed log, the terminal report,
# the machine-local copy, and the xref table — as a pure function of the results.
# The gate writes only when the results have changed, and only after a fresh
# run agrees with what it wrote (#249): one run on a clean tree,
# zero writes; a changed tree writes the new values and confirms with a genuinely
# fresh run (the section cache bypassed internally, regardless of --fresh) — at
# most three runs total, short-circuiting the moment a run agrees with what was
# just written. Results that will not settle within that budget are a fault, not
# a commit: the run exits non-zero naming the file. Nothing is ever staged.
#
# Tiers: code + schema are deterministic on any clone (the committed log carries
# only these); data is machine-local, advisory. Whether the hook is installed is a
# machine-local fact that `corpus-yoga prerequisites` reports as an ERROR; a hook that RUNS
# while being the outdated form is refused below, since only a running hook can say so.
# Read a failure:
# git diff rsc/test/run.log

set -euo pipefail

SELF='src/test/dev/run.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

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
# (toplevel == this repo). the prepare-commit-msg hook stays home-anchored on purpose:
# the machine binding it reads is machine-scoped and absent from worktrees.
# A root this script computed is not a root until something says so: a climb left
# short by a move makes REPO_DIR unequal to every toplevel, and the re-exec below
# then hands the same file back to itself. exec replaces the process image, so a
# loop of them consumes no memory, no PIDs and no stack — nothing above this script
# can see it, and the gate HANGS rather than fails. Assert the root, and never
# re-exec this very file: -ef is the same-file test, which is what the guard means.
[[ -f "$REPO_DIR/corpus-yoga" ]] || { echo "ERROR: $REPO_DIR is not a repo root — this script's climb is wrong." >&2; exit 1; }
TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -n "$TOPLEVEL" && "$TOPLEVEL" != "$REPO_DIR" ]]; then
  if [[ -x "$TOPLEVEL/src/test/dev/run.sh" ]] && ! [[ "$TOPLEVEL/src/test/dev/run.sh" -ef "${BASH_SOURCE[0]}" ]]; then
    exec "$TOPLEVEL/src/test/dev/run.sh" "$@"
  fi
  # REFUSE, never fall through (PR #25 review): running the home gate against
  # the home tree inside the other tree's git context is exactly the chimera
  # this guard abolishes — a fallthrough would restore it silently, with the
  # same unsatisfiable ERROR that cost a day. A loud refusal is recoverable.
  echo "ERROR: cannot gate $TOPLEVEL — no executable src/test/dev/run.sh there." >&2
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
# The test is EQUALITY with rsc/test/pre-commit-hook.sh, the one authority on what an
# installed hook is — not a pattern, which a longer or conditional hook would satisfy
# while doing something else entirely. `corpus-yoga prerequisites` asks the same question of the
# same file.
if [[ -n "${GIT_INDEX_FILE:-}" ]]; then
  hook_path="$(git -C "$REPO_DIR" rev-parse --git-path hooks/pre-commit 2>/dev/null || true)"
  [[ -z "$hook_path" || "$hook_path" = /* ]] || hook_path="$REPO_DIR/$hook_path"
  if [[ -n "$hook_path" ]] && ! cmp -s "$hook_path" "$REPO_DIR/rsc/test/pre-commit-hook.sh"; then
    echo "ERROR: this commit ran an OUTDATED pre-commit hook." >&2
    echo "       It points at a file rather than naming \`corpus-yoga test run\`, so renaming that" >&2
    echo "       file would disarm the gate in silence. Nothing is wrong with the change." >&2
    echo "       → run: ./corpus-yoga test install-hook" >&2
    exit 1
  fi
fi

# The artifacts run.py rewrites on every run — what the staleness check below
# compares against the index.
ARTIFACTS=(rsc/test/run.log rsc/test/xref.csv)

# --settle: the merge's settle face (#485) - regenerate the artifacts and
# SUCCEED; staging is the invoker's next act. The staleness veto below exists
# for a human about to commit; the merge performs the veto's remedy itself, so
# handing it the refusal would be the machinery borrowing a human-facing ERROR.
# Internal: invoked directly by forge.sh's merge, not declared on the surface.
SETTLE=0

parse_args() {
  case "${1:-}" in
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
  esac
}

main() {
  parse_args "$@"
  local -a forward=()
  local arg
  for arg in "$@"; do
    if [[ "$arg" == --settle ]]; then SETTLE=1; else forward+=("$arg"); fi
  done
  set -- ${forward[@]+"${forward[@]}"}

  mkdir -p "$REPO_DIR/tmp/cache"

  # One invocation. run.py settles internally (#249): every output is built in
  # memory; the committed artifacts (rsc/test/run.log, rsc/test/xref.csv) are
  # written only when their bytes differ from disk, and a write stands only once
  # a genuinely fresh recomputation agrees with it — at most three runs inside
  # this one invocation, faulting if the results will not settle. The full
  # report goes to tmp/logs/test/run/, the terminal tail prints here, and
  # the exit code is the verdict.
  local rc=0
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/dev/run.py" "$@" || rc=$?

  # The artifacts' currency, guarded without touching anything. Deleting the old
  # `git add` deleted a guarantee along with the rudeness: it silently ensured
  # every commit carried freshly regenerated artifacts. Nothing reads the
  # COMMITTED log — check_score reads live counts — so a forgotten stage would
  # decay the byte-identical-on-any-clone contract one commit at a time, with no
  # check ever noticing. Refuse and tell; never stage on someone's behalf.
  # Worktree-vs-index is the right comparison: what is about to be committed must
  # be what a fresh run produces. Unchanged artifacts never diff, so this is
  # silent until it matters.
  if (( ! SETTLE )) && ! git -C "$REPO_DIR" diff --quiet -- "${ARTIFACTS[@]}" 2>/dev/null; then
    echo "ERROR: the regenerated artifacts are not staged — what would be committed is stale:" >&2
    printf '    → run: git add %s\n' "${ARTIFACTS[*]}" >&2
    rc=1
  fi

  exit $rc
}

main "$@"
