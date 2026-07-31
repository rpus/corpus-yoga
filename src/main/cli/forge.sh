#!/usr/bin/env bash
# forge.sh (yoga forge) — the forge's merge settings, and the operations that obey them.
#
# The settings decide how main's history is composed and live on the SERVER, where no clone
# sees them and no git config holds them; src/main/cli/forge/forge.csv declares them.
#
# Usage:
#   yoga forge                 # declared vs live
#   yoga forge --tsv           # every row bare forge shows, section-tagged, for a program
#   yoga forge sync [--apply]  # make the forge agree with src/main/cli/forge/forge.csv
#   yoga forge merge <pr> [--dry-run]   # check everything, then squash-merge that PR
#   yoga forge prune [--apply] # forget what the forge no longer has
#
# merge names a POSTCONDITION — PR merged, this checkout on the base, the base holding the
# squash, the head branch gone from here — and converges on it, logging the run.
#
# prune forgets both leavings of a squash-and-delete: a local branch whose work the base
# holds, and a tracking ref for a branch the forge deleted. sync and prune are
# --apply-gated. merge passes NO message flags: under COMMIT_MESSAGES the body comes from
# the branch's commits, keeping the Signature lines a hand-written --body would discard.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DECLARED="$REPO_DIR/src/main/cli/forge/forge.csv"
# shellcheck source=src/main/send.sh
source "$REPO_DIR/src/main/send.sh"   # may_send / assert_may_send — the shell face (#29)

# rows: STATUS \t key \t detail \t remedy — the ONE derivation, rendered by two callers
# (this script's status, and `yoga prerequisites`' machine report).
reconcile() {
  [[ -f "$DECLARED" ]] || { echo -e "UNVERIFIED\tforge.csv\tno src/main/cli/forge/forge.csv — nothing declared\t"; return; }
  command -v gh &>/dev/null || { echo -e "UNVERIFIED\tgh\tgh not found (install: brew install gh)\t"; return; }
  may_send || { echo -e "UNVERIFIED\tforge\tYOGA_NO_SEND=1 refuses this send: gh api (live settings unread)\t"; return; }
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

# rows: STATUS \t branch \t detail — every LOCAL branch, and what the forge says about it.
# Discovery runs branch → PR, not PR → branch: a branch you had forgotten is exactly the one
# whose PR number you cannot recall, so a listing keyed on the PR is unreachable when it is
# needed. One `gh pr list` indexes every PR by its head branch; per-branch queries would cost
# a round trip each to answer the same question.
branches() {
  command -v gh &>/dev/null || return 0
  may_send || return 0
  local prs
  prs="$(cd "$REPO_DIR" && gh pr list --state all --limit 200 \
    --json number,state,headRefName,headRefOid 2>/dev/null)" || return 0
  local b tip pr_json n st oid holder base
  base="$(base_branch)"
  while read -r b; do
    [[ -n "$b" ]] || continue
    tip="$(git -C "$REPO_DIR" rev-parse "refs/heads/$b")"
    holder="$(git -C "$REPO_DIR" worktree list --porcelain | awk -v r="refs/heads/$b" '
      /^worktree /{w=$2} /^branch /{ if ($2==r) print w }')"
    pr_json="$(jq -c --arg b "$b" 'map(select(.headRefName == $b)) | sort_by(.number) | last // empty' <<< "$prs")"
    if [[ -z "$pr_json" ]]; then
      echo -e "KEPT\t$b\tno PR on the forge refers to it"
      continue
    fi
    n=$(jq -r .number <<< "$pr_json"); st=$(jq -r .state <<< "$pr_json"); oid=$(jq -r .headRefOid <<< "$pr_json")
    if [[ "$st" == CLOSED ]]; then
      # A closed PR is not an abandoned branch. It may hold the only copy of that work, or
      # it may have been folded into another PR and closed as redundant, and "#N is CLOSED"
      # does not distinguish them. Containment does, and git can be asked: ancestry first,
      # then patch-id, which a rebase or a cherry-pick preserves where the hash does not.
      if [[ -n "$holder" ]]; then
        echo -e "KEPT\t$b\t#$n is CLOSED, but the branch is checked out at $holder"
      elif git -C "$REPO_DIR" merge-base --is-ancestor "$tip" "refs/heads/$base" 2>/dev/null; then
        echo -e "DELETABLE\t$b\t#$n is CLOSED, and ${tip:0:8} is contained in $base"
      else
        local unique
        unique="$(git -C "$REPO_DIR" cherry "$base" "$b" 2>/dev/null | grep -c '^+' || true)"
        if [[ "$unique" == 0 ]]; then
          echo -e "DELETABLE\t$b\t#$n is CLOSED, and every commit of it is in $base by patch"
        else
          echo -e "KEPT\t$b\t#$n is CLOSED, and $unique commit(s) of it are not in $base — folded into another PR, or the only copy; git log $base..$b says which"
        fi
      fi
    elif [[ "$st" != MERGED ]]; then
      echo -e "KEPT\t$b\t#$n is $st"
    elif [[ -n "$holder" ]]; then
      echo -e "KEPT\t$b\t#$n merged, but the branch is checked out at $holder"
    elif git -C "$REPO_DIR" merge-base --is-ancestor "$tip" "$oid" 2>/dev/null; then
      echo -e "DELETABLE\t$b\t#$n merged, and ${tip:0:8} is contained in the merged head ${oid:0:8}"
    else
      echo -e "KEPT\t$b\t#$n merged, but ${tip:0:8} is not contained in it — it holds commits the squash did not"
    fi
  done < <(git -C "$REPO_DIR" for-each-ref --format='%(refname:short)' refs/heads/ \
             | grep -v "^$base\$")
}

# rows: STATUS \t ref \t detail — the remote-tracking refs this checkout still holds for
# branches the forge no longer has. delete_branch_on_merge removes the branch server-side
# the moment a PR lands, and nothing local notices: `refs/remotes/origin/<gone>` survives
# until some `git fetch --prune`. It is the same drift as a merged local branch surviving —
# state this checkout holds about a thing that is gone — so forge names it in the same voice.
stale_tracking() {
  local out line ref
  # Asking git costs a round trip to the remote, and a failure must not read as "nothing
  # stale": an absent section is indistinguishable from a clean one. Say UNVERIFIED, as
  # reconcile does for the settings it cannot see.
  if ! may_send; then
    echo -e "UNVERIFIED\torigin\tYOGA_NO_SEND=1 refuses this send: git remote prune --dry-run (tracking refs unverified)"
    return
  fi
  if ! out="$(git -C "$REPO_DIR" remote prune --dry-run origin 2>/dev/null)"; then
    echo -e "UNVERIFIED\torigin\tunreachable — cannot tell which tracking refs the forge has dropped"
    return
  fi
  while read -r line; do
    [[ "$line" == *"[would prune]"* ]] || continue
    ref="${line##* }"
    echo -e "STALE\t$ref\tthe forge no longer has this branch; this checkout still tracks it"
  done <<< "$out"
}

# rows: STATUS \t key \t detail \t remedy — whether this checkout can gate what it commits.
# The AUTHORITY is rsc/test/pre-commit-hook.sh, the same file `yoga prerequisites` and the
# gate compare against; this reads it rather than holding a second opinion.
gate() {
  local hook accepted="$REPO_DIR/rsc/test/pre-commit-hook.sh"
  hook="$(git -C "$REPO_DIR" rev-parse --git-path hooks/pre-commit 2>/dev/null || true)"
  [[ -z "$hook" || "$hook" = /* ]] || hook="$REPO_DIR/$hook"
  if [[ -n "$hook" ]] && cmp -s "$hook" "$accepted"; then
    echo -e "OK\tpre-commit\ta copy of rsc/test/pre-commit-hook.sh\t"
  else
    echo -e "WRONG\tpre-commit\tnot the accepted hook — commits from here are not being vetted\tyoga test install-hook"
  fi
}

# the branch a merge lands on, and the one `merge` returns you to — asked of the forge, not
# assumed to be `main`
base_branch() {
  may_send || { echo main; return; }
  (cd "$REPO_DIR" && gh repo view --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null) || echo main
}

status() {
  echo "forge settings — declared: src/main/cli/forge/forge.csv; live: this checkout's remote"
  local st key detail remedy drift=0
  while IFS=$'\t' read -r st key detail remedy; do
    [[ -z "$st" ]] && continue
    case "$st" in
      OK)    echo "  ✓ $key: $detail" ;;
      DRIFT) echo "  ✗ $key: $detail"; echo "    → run: $remedy"; drift=1 ;;
      *)     echo "  – $key: $detail" ;;
    esac
  done < <(reconcile)

  # The branches this checkout still holds. A merged branch surviving here is drift of the
  # same kind as a forge setting that disagrees with src/main/cli/forge/forge.csv: reconcilable state, and
  # this is where it is named.
  local rows
  rows="$(branches)"
  if [[ -n "$rows" ]]; then
    echo "local branches — what the forge says about each"
    local d
    while IFS=$'\t' read -r st key detail; do
      [[ -z "$st" ]] && continue
      case "$st" in
        DELETABLE) echo "  ✗ $key: $detail"; d=1 ;;
        *)         echo "  – $key: $detail" ;;
      esac
    done <<< "$rows"
    [[ -z "${d:-}" ]] || echo "    → run: yoga forge prune"
  fi

  local stale
  stale="$(stale_tracking)"
  if [[ -n "$stale" ]]; then
    echo "remote-tracking refs — branches the forge has deleted"
    local any=""
    while IFS=$'\t' read -r st key detail; do
      [[ -z "$st" ]] && continue
      case "$st" in
        STALE) echo "  ✗ $key: $detail"; any=1 ;;
        *)     echo "  – $key: $detail" ;;
      esac
    done <<< "$stale"
    [[ -z "$any" ]] || { echo "    → run: yoga forge prune"; drift=1; }
  fi

  # Whether this checkout can gate is forge business: merging lands work on a base every
  # clone pulls, and a machine whose pre-commit hook is absent or outdated has been
  # committing unvetted — so what it is about to land was never checked. The AUTHORITY is
  # rsc/test/pre-commit-hook.sh, the same file `yoga prerequisites` and the gate compare
  # against; this reads that file rather than holding a second opinion about it.
  echo "this checkout's gate — the hook that vets what you commit"
  while IFS=$'\t' read -r st key detail remedy; do
    [[ -z "$st" ]] && continue
    if [[ "$st" == OK ]]; then
      echo "  ✓ $key: $detail"
    else
      echo "  ✗ $key: $detail"; echo "    → run: $remedy"; drift=1
    fi
  done < <(gate)
  return $drift
}

# Delete exactly what `status` marked DELETABLE — one predicate, so what is listed and what
# is removed cannot disagree. A squash makes a merged branch look unmerged to git, so
# `git branch -d` refuses and only -D will do it; the safety is the containment test above,
# never git's opinion.
prune() {
  local apply="" st key detail n=0
  [[ "${1-}" == "--apply" ]] && apply=1
  while IFS=$'\t' read -r st key detail; do
    [[ "$st" == DELETABLE ]] || continue
    n=$((n + 1))
    if [[ -n "$apply" ]]; then
      git -C "$REPO_DIR" branch -D "$key" >/dev/null && echo "deleted $key — $detail"
    else
      echo "would delete $key — $detail"
    fi
  done < <(branches)
  local stale_rows ref
  stale_rows="$(stale_tracking)"
  while IFS=$'\t' read -r st ref _; do
    [[ "$st" == STALE ]] || continue
    n=$((n + 1))
    if [[ -n "$apply" ]]; then
      git -C "$REPO_DIR" update-ref -d "refs/remotes/$ref" && echo "forgot $ref — the forge no longer has it"
    else
      echo "would forget $ref — the forge no longer has it"
    fi
  done <<< "$stale_rows"

  if [[ "$n" == 0 ]]; then
    echo 'nothing to prune — yoga forge says why for each branch it keeps'
  elif [[ -z "$apply" ]]; then
    echo "--- $n item(s); nothing removed. Add --apply to remove them"
  fi
}

sync() {
  local apply=""
  [[ "${1-}" == "--apply" ]] && apply=1
  # G19: the extent before, the effect, the extent after — so the run says what it changed
  # rather than asserting that it did.
  # The write IS the work under --apply: refuse loudly before any extent is shown,
  # as assert_may_send does in python (#29). The dry run is a read and degrades below.
  [[ "${1-}" == "--apply" ]] && ! assert_may_send "gh api -X PATCH (forge sync --apply)" && exit 1
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
    # An extent of UNVERIFIED rows is not agreement: saying "no drift" over settings
    # nobody read would be a lie (G19 needs a real extent). Refused/offline exits loudly.
    if ! printf '%s\n' "$rows" | grep -q $'^OK\t'; then
      echo "yoga forge sync: the live settings could not be read — nothing verified, nothing to agree" >&2
      return 1
    fi
    echo "no drift — the forge already agrees with src/main/cli/forge/forge.csv; nothing to do"
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

  # The one operation here that writes to a server other people see, and its whole audit
  # trail was terminal scrollback. Path per the command/verb rule (#54).
  local log
  log="$REPO_DIR/tmp/logs/forge/merge/$(date -u '+%Y-%m-%dT%H:%M:%SZ').log"
  mkdir -p "$(dirname "$log")"
  exec > >(tee -a "$log") 2>&1
  echo "yoga forge merge $pr — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  # 0. the sends ARE the work here (gh pr view, gh pr merge): refuse loudly, first (#29)
  assert_may_send "gh pr view / gh pr merge (yoga forge merge)" || exit 1

  # 1. the forge itself: merging under undeclared settings composes main by rules nobody wrote
  status || { echo "yoga forge merge: refused — settle the ✗ lines above first; each names its own remedy" >&2; exit 1; }

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
  # merge names a POSTCONDITION, so an already-merged PR is not an error: the forge half is
  # done and the local half may not be. Converge the rest rather than refusing and leaving
  # the caller to finish it by hand — which is how four merged branches came to sit here.
  local already=""
  if [[ "$state" == MERGED ]]; then
    already=1
    echo "  already merged on the forge — converging the local half"
  else
    [[ "$state"     == OPEN      ]] || { echo "yoga forge merge: #$n is $state — nothing to merge" >&2; exit 1; }
    [[ "$draft"     == false     ]] || { echo "yoga forge merge: #$n is a draft — mark it ready first" >&2; exit 1; }
    [[ "$mergeable" == MERGEABLE ]] || { echo "yoga forge merge: #$n is $mergeable ($mstate) — resolve that first; gh would fail or prompt" >&2; exit 1; }
  fi
  # BEHIND matters for more than tidiness: a squash of an up-to-date branch lands exactly
  # the branch's tree, which its own pre-commit hook already gated. Behind main, the merged
  # tree is a combination nothing has ever checked.
  [[ -n "$already" || "$mstate" == CLEAN ]] || { echo "yoga forge merge: #$n is $mstate — a squash of a branch that is not up to date lands a tree no gate has seen; rebase it onto main first" >&2; exit 1; }

  # 2b. the postcondition moves HEAD to the base branch, so the tree must be clean FIRST:
  # a merge that lands and then cannot tidy up is worse than one that refuses early.
  local base current
  base="$(base_branch)"
  current="$(git -C "$REPO_DIR" branch --show-current)"
  local dirty="" dirty_files=""
  dirty_files="$(git -C "$REPO_DIR" status --porcelain)"
  [[ -z "$dirty_files" ]] || dirty=1

  # 3. the INTENT: exactly what will land, since afterwards the parts are unreachable
  echo
  echo "the message the forge will assemble (squash_merge_commit_message: COMMIT_MESSAGES):"
  echo "  $title (#$n)"
  jq -r '.commits[] | "  * " + (.messageHeadline)' <<< "$json"
  local sigs
  sigs=$(jq -r '[.commits[] | select(.messageBody | test("(^|\n)Signature:"))] | length' <<< "$json")
  echo "  — $(jq -r '.commits | length' <<< "$json") commit(s), $sigs carrying a Signature"
  [[ "$sigs" -gt 0 ]] || echo "  ⚠ no commit carries a Signature: main would gain history no session can be joined to"

  echo
  echo "the state this leaves behind:"
  [[ -n "$already" ]] && echo "  #$n is merged into $base (already)" \
                      || echo "  #$n merged into $base"
  [[ "$current" == "$head" ]] && echo "  this checkout moves from $head to $base" \
                             || echo "  this checkout stays on $current"
  echo "  $base fast-forwarded to include it"
  echo "  $head deleted here, if the merged head contains it"
  if [[ -n "$dirty" ]]; then
    echo "  ⚠ this checkout has uncommitted changes — a real run refuses here:"
    local f
    while IFS= read -r f; do echo "      $f"; done <<< "$dirty_files"
  fi
  [[ -z "$dry" ]] || { echo; echo "--dry-run: nothing merged"; return 0; }

  # a dry run reports the dirty tree; a real one refuses on it, because the postcondition
  # moves HEAD, and a merge that lands and then cannot tidy up is worse than one that stops
  [[ -z "$dirty" ]] || { echo "yoga forge merge: this checkout has uncommitted changes — the merge ends on $base, and moving HEAD would carry or refuse them; commit or stash first" >&2; exit 1; }

  # 4. the effect. No --subject, no --body: the forge assembles the message from the
  # commits, which is where the signatures are. --match-head-commit closes the race
  # between the head just inspected and the head merged.
  echo
  # off the branch BEFORE merging: a branch checked out here cannot be deleted, and the
  # tidy-up is part of what `merge` promises, not a courtesy attempted afterwards
  if [[ "$current" == "$head" ]]; then
    git -C "$REPO_DIR" checkout --quiet "$base" || {
      echo "yoga forge merge: could not switch to $base — nothing merged" >&2; exit 1; }
    echo "switched to $base"
  fi
  if [[ -z "$already" ]]; then
    cd "$REPO_DIR" && gh pr merge "$n" --squash --match-head-commit "$oid" || return $?
  fi

  # 5. the extent afterwards. delete_branch_on_merge removes the REMOTE branch; the local
  # one survives, and a squash makes it look unmerged to git — so `git branch -d` refuses
  # and only -D will do it. The safety therefore cannot come from git's opinion: it comes
  # from comparing the local tip with the head we just merged. Equal means everything local
  # is in the squash; different means unpushed work, and the branch stays.
  echo
  # fetch WITHOUT pruning: the fast-forward below needs origin/$base, but pruning here
  # asks the server before it has finished deleting the head branch (see the end).
  git -C "$REPO_DIR" fetch --quiet origin || true
  # the base must actually HOLD the squash here, or the next thing anyone types is a manual
  # pull — the same residue in another shape
  if git -C "$REPO_DIR" merge --ff-only --quiet "origin/$base" 2>/dev/null; then
    echo "local: $base fast-forwarded to $(git -C "$REPO_DIR" rev-parse --short HEAD)"
  else
    echo "local: $base NOT fast-forwarded — it has diverged from origin/$base; reconcile it yourself"
  fi

  # the head branch, judged by the SAME derivation `yoga forge` and `prune` use, so what is
  # listed, what is pruned, and what a merge tidies cannot disagree
  local st key detail found=""
  while IFS=$'\t' read -r st key detail; do
    [[ "$key" == "$head" ]] || continue
    found=1
    if [[ "$st" == DELETABLE ]]; then
      git -C "$REPO_DIR" branch -D "$head" >/dev/null && echo "local: $head deleted — $detail"
    else
      echo "local: $head kept — $detail"
    fi
  done < <(branches)
  [[ -n "$found" ]] || echo "local: no branch $head here — nothing to prune"

  # ONE prune, at the LATEST moment. delete_branch_on_merge removes the remote branch
  # ASYNCHRONOUSLY after the squash: a prune taken earlier asks while the branch still
  # exists, keeps the tracking ref, and leaves behind exactly the drift `yoga forge`
  # reports — the merge creating the mess its own command exists to clear. By here the
  # deletion has had the squash, the fetch, the fast-forward and the local delete to land.
  local tracked=""
  git -C "$REPO_DIR" show-ref --verify --quiet "refs/remotes/origin/$head" && tracked=1
  git -C "$REPO_DIR" remote prune origin >/dev/null 2>&1 || true
  if [[ -n "$tracked" ]]; then
    if git -C "$REPO_DIR" show-ref --verify --quiet "refs/remotes/origin/$head"; then
      echo "local: origin/$head still tracked — the forge had not dropped it yet; yoga forge prune"
    else
      echo "local: origin/$head forgotten — the forge has dropped it"
    fi
  fi

  # 6. adoption: the machine report, run rather than remembered. What a merged idea
  # asks of THIS machine is machine-local state, and prerequisites is the surface that
  # owns machine-local state end to end — report with remedies, sync --apply as the
  # enacting verb the USER runs. The merge does not enact adoption; it surfaces it:
  # a PR whose adoption prerequisites cannot see should have extended prerequisites.
  echo
  echo "the machine, post-merge — adoption lives in these prescriptions (yoga prerequisites):"
  "$REPO_DIR/yoga" prerequisites || true

  # The trailing half of the bracket (G19), shown rather than asserted: which branch you
  # are on and what the tree holds. A merge that leaves a modified artifact behind will
  # block the next pull, and nothing said so until the pull failed.
  echo
  echo "this checkout, now:"
  git -C "$REPO_DIR" status
}

case "${1-}" in
  '')        status ;;
  --tsv)     reconcile     | sed 's/^/settings\t/'
             branches      | sed 's/^/branch\t/'
             stale_tracking| sed 's/^/tracking\t/'
             gate          | sed 's/^/gate\t/' ;;
  sync)      shift; sync "$@" ;;
  prune)     shift; prune "$@" ;;
  merge)     shift; merge "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "yoga forge: unknown argument: $1 (try: yoga forge --help)" >&2; exit 1 ;;
esac
