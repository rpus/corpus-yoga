#!/usr/bin/env bash
# forge.sh (yoga forge) — the forge's merge settings, and the operations that obey them.
#
# The settings decide how main's history is composed and live on the SERVER: no clone can
# see them, no git config holds them. rsc/forge.csv declares them.
#
# Usage:
#   yoga forge                 # declared vs live
#   yoga forge --tsv           # the same rows, for a reader that is a program
#   yoga forge sync [--apply]  # make the forge agree with rsc/forge.csv
#   yoga forge merge <pr> [--dry-run]   # check everything, then squash-merge that PR
#
# sync is --apply-gated because it writes OUTSIDE the repo, to a server other people see —
# the consent `agent receive` requires, for the same reason.
#
# merge passes NO message flags. squash_merge_commit_message is COMMIT_MESSAGES: the body
# is assembled from the branch's commits, each keeping its Signature line — the join key
# into the captured session corpus. A hand-written --body discards every one of them,
# which is how seven merges landed unsigned on 2026-07-25 while the branch commits beneath
# them were correctly stamped.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DECLARED="$REPO_DIR/rsc/forge.csv"

# rows: STATUS \t key \t detail \t remedy — the ONE derivation, rendered by two callers
# (this script's status, and PREREQUISITES' machine report).
reconcile() {
  [[ -f "$DECLARED" ]] || { echo -e "UNVERIFIED\tforge.csv\tno rsc/forge.csv — nothing declared\t"; return; }
  command -v gh &>/dev/null || { echo -e "UNVERIFIED\tgh\tgh not found (install: brew install gh)\t"; return; }
  local live
  # quoted: {owner}/{repo} are gh's own placeholders, resolved from this checkout's
  # remote — never brace-expansion, and never a hard-coded (fork-specific) slug
  if ! live="$(cd "$REPO_DIR" && gh api "repos/{owner}/{repo}" 2>/dev/null)"; then
    echo -e "UNVERIFIED\tforge\tunreachable (offline, no GitHub remote, or: gh auth login)\t"
    return
  fi
  printf '%s' "$live" | python3 -c '
import csv, json, sys
live = json.load(sys.stdin)
slug = live.get("full_name") or "{owner}/{repo}"
def norm(v):
    return "true" if v is True else "false" if v is False else str(v)
for r in csv.DictReader(open(sys.argv[1])):
    key, want = r["setting"], r["value"]
    got = norm(live.get(key))
    if got == want:
        print("OK", key, want, "", sep="\t")
    else:
        flag = "-F" if want in ("true", "false") else "-f"   # -F types booleans, -f strings
        print("DRIFT", key, "declared " + want + ", live " + got,
              "gh api -X PATCH repos/" + slug + " " + flag + " " + key + "=" + want, sep="\t")
' "$DECLARED" 2>/dev/null || echo -e "UNVERIFIED\tforge.csv\tunreadable or malformed\t"
}

status() {
  echo "forge settings — declared: rsc/forge.csv; live: this checkout's remote"
  local st key detail remedy drift=0
  while IFS=$'\t' read -r st key detail remedy; do
    [[ -z "$st" ]] && continue
    case "$st" in
      OK)    echo "  ✓ $key: $detail" ;;
      DRIFT) echo "  ✗ $key: $detail"; echo "    → run: $remedy"; drift=1 ;;
      *)     echo "  – $key: $detail" ;;
    esac
  done < <(reconcile)
  return $drift
}

sync() {
  local apply=""
  [[ "${1-}" == "--apply" ]] && apply=1
  # G19: the extent before, the effect, the extent after — so the run says what it changed
  # rather than asserting that it did.
  local rows drift=0
  rows="$(reconcile)"
  echo "before:"
  printf '%s\n' "$rows" | while IFS=$'\t' read -r st key detail _; do
    [[ -n "$st" ]] && echo "  $([[ "$st" == OK ]] && echo ✓ || echo ✗) $key: $detail"
  done
  while IFS=$'\t' read -r st key detail remedy; do
    [[ "$st" == DRIFT ]] || continue
    drift=1
    if [[ -n "$apply" ]]; then
      echo "  → $remedy"
      (cd "$REPO_DIR" && eval "$remedy" >/dev/null) || { echo "yoga forge sync: $key failed — settings unchanged for it" >&2; exit 1; }
    else
      echo "  would run: $remedy"
    fi
  done <<< "$rows"
  if [[ "$drift" == 0 ]]; then
    echo "no drift — the forge already agrees with rsc/forge.csv; nothing to do"
    return 0
  fi
  [[ -n "$apply" ]] || { echo "--dry-run by default: nothing changed. Re-run with --apply."; return 0; }
  echo "after:"
  reconcile | while IFS=$'\t' read -r st key detail _; do
    [[ -n "$st" ]] && echo "  $([[ "$st" == OK ]] && echo ✓ || echo ✗) $key: $detail"
  done
}

# Everything checkable, BEFORE the irreversible step. gh squashes server-side, so nothing
# local is half-done — but delete_branch_on_merge means the branch and its individual
# commits stop being reachable the moment it succeeds. A check after that is worthless, and
# the assembled message is the one thing that cannot be inspected afterwards.
merge() {
  local pr="${1-}" dry=""
  [[ "${2-}" == "--dry-run" ]] && dry=1
  [[ "$pr" == "--dry-run" ]] && { echo "yoga forge merge: --dry-run comes after the PR" >&2; exit 1; }
  [[ -n "$pr" ]] || { echo "yoga forge merge: which PR? (a number, a URL, or a branch)" >&2; exit 1; }

  # 1. the forge itself: merging under undeclared settings composes main by rules nobody wrote
  status || { echo "yoga forge merge: forge settings drift — reconcile first (yoga forge sync --apply)" >&2; exit 1; }

  # 2. the PR's own state, from the forge rather than from optimism
  local json
  json="$(cd "$REPO_DIR" && gh pr view "$pr" \
    --json number,title,state,isDraft,mergeable,mergeStateStatus,headRefName,headRefOid,commits 2>/dev/null)" \
    || { echo "yoga forge merge: no such PR: $pr" >&2; exit 1; }
  local n title state draft mergeable mstate head oid
  n=$(jq -r .number <<< "$json");        title=$(jq -r .title <<< "$json")
  state=$(jq -r .state <<< "$json");     draft=$(jq -r .isDraft <<< "$json")
  mergeable=$(jq -r .mergeable <<< "$json"); mstate=$(jq -r .mergeStateStatus <<< "$json")
  head=$(jq -r .headRefName <<< "$json"); oid=$(jq -r .headRefOid <<< "$json")
  echo
  echo "PR #$n $title"
  echo "  head: $head @ ${oid:0:8} · state: $state · mergeable: $mergeable/$mstate"
  [[ "$state"     == OPEN      ]] || { echo "yoga forge merge: #$n is $state — nothing to merge" >&2; exit 1; }
  [[ "$draft"     == false     ]] || { echo "yoga forge merge: #$n is a draft — mark it ready first" >&2; exit 1; }
  [[ "$mergeable" == MERGEABLE ]] || { echo "yoga forge merge: #$n is $mergeable ($mstate) — resolve that first; gh would fail or prompt" >&2; exit 1; }
  # BEHIND matters for more than tidiness: a squash of an up-to-date branch lands exactly
  # the branch's tree, which its own pre-commit hook already gated. Behind main, the merged
  # tree is a combination nothing has ever checked.
  [[ "$mstate"    == CLEAN     ]] || { echo "yoga forge merge: #$n is $mstate — a squash of a branch that is not up to date lands a tree no gate has seen; rebase it onto main first" >&2; exit 1; }

  # 3. the INTENT: exactly what will land, since afterwards the parts are unreachable
  echo
  echo "the message the forge will assemble (squash_merge_commit_message: COMMIT_MESSAGES):"
  echo "  $title (#$n)"
  jq -r '.commits[] | "  * " + (.messageHeadline)' <<< "$json"
  local sigs
  sigs=$(jq -r '[.commits[] | select(.messageBody | test("(^|\n)Signature:"))] | length' <<< "$json")
  echo "  — $(jq -r '.commits | length' <<< "$json") commit(s), $sigs carrying a Signature"
  [[ "$sigs" -gt 0 ]] || echo "  ⚠ no commit carries a Signature: main would gain history no session can be joined to"

  [[ -z "$dry" ]] || { echo; echo "--dry-run: nothing merged"; return 0; }

  # 4. the effect. No --subject, no --body: the forge assembles the message from the
  # commits, which is where the signatures are. --match-head-commit closes the race
  # between the head just inspected and the head merged.
  echo
  cd "$REPO_DIR" && gh pr merge "$n" --squash --match-head-commit "$oid" || return $?

  # 5. the extent afterwards. delete_branch_on_merge removes the REMOTE branch; the local
  # one survives, and a squash makes it look unmerged to git — so `git branch -d` refuses
  # and only -D will do it. The safety therefore cannot come from git's opinion: it comes
  # from comparing the local tip with the head we just merged. Equal means everything local
  # is in the squash; different means unpushed work, and the branch stays.
  echo
  git -C "$REPO_DIR" fetch --quiet --prune origin || true
  local local_tip
  if ! local_tip="$(git -C "$REPO_DIR" rev-parse --verify --quiet "refs/heads/$head")"; then
    echo "local: no branch $head here — nothing to prune"
    return 0
  fi
  local holder
  holder="$(git -C "$REPO_DIR" worktree list --porcelain | awk -v b="refs/heads/$head" '
    /^worktree /{w=$2} /^branch /{ if ($2==b) print w }')"
  if [[ -n "$holder" ]]; then
    echo "local: $head kept — still checked out at $holder"
  elif git -C "$REPO_DIR" merge-base --is-ancestor "$local_tip" "$oid"; then
    # ANCESTOR, not equal: a local branch merely BEHIND the merged head is entirely inside
    # the squash, so deleting it loses nothing. Testing equality kept such a branch and
    # said it "holds commits the squash did not" — which was simply false.
    git -C "$REPO_DIR" branch -D "$head" >/dev/null \
      && echo "local: $head deleted — ${local_tip:0:8} is contained in the merged head ${oid:0:8}"
  else
    echo "local: $head KEPT at ${local_tip:0:8} — not an ancestor of the merged head ${oid:0:8}, so it holds commits the squash did not"
  fi
}

case "${1-}" in
  '')        status ;;
  --tsv)     reconcile ;;
  sync)      shift; sync "$@" ;;
  merge)     shift; merge "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "yoga forge: unknown argument: $1 (try: yoga forge --help)" >&2; exit 1 ;;
esac
