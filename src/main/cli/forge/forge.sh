#!/usr/bin/env bash
# forge.sh (yoga forge) — the forge's merge settings, and the operations that obey them.
#
# Usage:
#   yoga forge                 # declared vs live
#   yoga forge sync [--apply]  # make the forge agree with src/main/cli/forge/forge.csv
#   yoga forge merge <pr>      # status; squash-merge that PR and converge this checkout; git status
#   yoga forge prune [--apply] # forget what the forge no longer has

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
DECLARED="$REPO_DIR/src/main/cli/forge/forge.csv"
# shellcheck source=src/main/send.sh
source "$REPO_DIR/src/main/send.sh"
# shellcheck source=src/main/enact.sh
source "$REPO_DIR/src/main/enact.sh"

# rows: STATUS \t key \t detail \t remedy — parsed by status() and `yoga prerequisites`
reconcile() {
  [[ -f "$DECLARED" ]] || { echo -e "UNVERIFIED\tforge.csv\tno src/main/cli/forge/forge.csv — nothing declared\t"; return; }
  command -v gh &>/dev/null || { echo -e "UNVERIFIED\tgh\tgh not found (install: brew install gh)\t"; return; }
  may_send || { echo -e "UNVERIFIED\tforge\tYOGA_NO_SEND=1 refuses this send: gh api (live settings unread)\t"; return; }
  local live
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
        flag = "-F" if want in ("true", "false") else "-f"
        print("DRIFT", key, "declared " + want + ", live " + got,
              "gh api -X PATCH repos/" + slug + " " + flag + " " + key + "=" + want, sep="\t")
' "$DECLARED" 2>/dev/null || echo -e "UNVERIFIED\tforge.csv\tunreadable or malformed\t"
}

superseding_force_push() {  # <pr-number> <tip>
  local n="$1" tip="$2" events event before
  # shellcheck disable=SC2016
  # the document is a file so the echo names it rather than reciting it (#301):
  # src/main/cli/forge/superseded-heads.graphql
  events="$(cd "$REPO_DIR" && quote gh api graphql -F owner='{owner}' -F repo='{repo}' -F number="$n" \
    -F query=@src/main/cli/forge/superseded-heads.graphql \
    --jq '.data.repository.pullRequest.timelineItems.nodes[]')" || return 0
  [[ -n "$events" ]] || return 0
  while IFS= read -r event; do
    [[ -n "$event" ]] || continue
    before="$(jq -r .beforeCommit.oid <<< "$event")"
    if [[ "$tip" == "$before" ]] || git -C "$REPO_DIR" merge-base --is-ancestor "$tip" "$before" 2>/dev/null; then
      printf '%s\n' "$event"
      return 0
    fi
  done <<< "$events"
}

# rows: STATUS \t branch \t detail [\t remedy] — parsed by status() and prune()
branches() {
  if ! command -v gh &>/dev/null; then
    echo -e "UNVERIFIED\tforge\tgh not installed — branch/PR state on the forge unverified"
    return
  fi
  if ! may_send; then
    echo -e "UNVERIFIED\tforge\tYOGA_NO_SEND=1 refuses this send: gh pr list (branch/PR state on the forge unverified)"
    return
  fi
  local prs
  prs="$(cd "$REPO_DIR" && gh pr list --state all --limit 200 \
    --json number,state,headRefName,headRefOid)" || {
    echo -e "UNVERIFIED\tforge\tgh pr list failed (its message above) — branch/PR state on the forge unverified"
    return
  }
  local b tip pr_json n st oid holder base
  base="$(base_branch)"
  while read -r b; do
    [[ -n "$b" ]] || continue
    tip="$(git -C "$REPO_DIR" rev-parse "refs/heads/$b")"
    holder="$(git -C "$REPO_DIR" worktree list --porcelain | awk -v r="refs/heads/$b" '
      /^worktree /{w=$2} /^branch /{ if ($2==r) print w }')"
    pr_json="$(jq -c --arg b "$b" 'map(select(.headRefName == $b)) | sort_by(.number) | last // empty' <<< "$prs")"
    if [[ -z "$pr_json" ]]; then
      # A name is not an identity: a worktree copy carries the same head under
      # another name, so ask the forge which PR has THIS commit as its head.
      pr_json="$(jq -c --arg oid "$tip" 'map(select(.headRefOid == $oid)) | sort_by(.number) | last // empty' <<< "$prs")"
      if [[ -n "$pr_json" ]]; then
        n=$(jq -r .number <<< "$pr_json"); st=$(jq -r .state <<< "$pr_json"); nm=$(jq -r .headRefName <<< "$pr_json")
        if [[ -n "$holder" ]]; then
          echo -e "KEPT\t$b\t#$n ($st) holds ${tip:0:8} as its head under the name $nm, but the branch is checked out at $holder\tgit checkout $base"
        else
          echo -e "DELETABLE\t$b\t#$n is $st and ${tip:0:8} is its head under the name $nm — the forge holds these commits"
        fi
      elif [[ -n "$holder" ]]; then
        echo -e "KEPT\t$b\tno PR on the forge refers to it, and the branch is checked out at $holder\tgit checkout $base"
      elif git -C "$REPO_DIR" merge-base --is-ancestor "$tip" "refs/heads/$base" 2>/dev/null; then
        echo -e "DELETABLE\t$b\tno PR refers to it, and ${tip:0:8} is contained in $base"
      else
        echo -e "KEPT\t$b\tno PR on the forge refers to it, and it holds commit(s) $base does not"
      fi
      continue
    fi
    n=$(jq -r .number <<< "$pr_json"); st=$(jq -r .state <<< "$pr_json"); oid=$(jq -r .headRefOid <<< "$pr_json")
    if [[ "$st" == CLOSED ]]; then
      if [[ -n "$holder" ]]; then
        echo -e "KEPT\t$b\t#$n is CLOSED, but the branch is checked out at $holder\tgit checkout $base"
      elif git -C "$REPO_DIR" merge-base --is-ancestor "$tip" "refs/heads/$base" 2>/dev/null; then
        echo -e "DELETABLE\t$b\t#$n is CLOSED, and ${tip:0:8} is contained in $base"
      else
        local unique
        unique="$(git -C "$REPO_DIR" cherry "$base" "$b" 2>/dev/null | grep -c '^+' || true)"
        if [[ "$unique" == 0 ]]; then
          echo -e "DELETABLE\t$b\t#$n is CLOSED, and every commit of it is in $base by patch"
        elif [[ "$tip" == "$oid" ]] || git -C "$REPO_DIR" merge-base --is-ancestor "$tip" "$oid" 2>/dev/null; then
          echo -e "DELETABLE\t$b\t#$n is CLOSED with ${tip:0:8} in its head — evidence-safe: the PR keeps its commits and diff, the reasoning lives in its thread"
        else
          echo -e "KEPT\t$b\t#$n is CLOSED, and $unique commit(s) of it are not in $base or in the PR's own head — this is the only copy; git log $base..$b says what"
        fi
      fi
    elif [[ "$st" != MERGED ]]; then
      if [[ "$st" == OPEN ]] && ! git -C "$REPO_DIR" merge-base --is-ancestor "refs/remotes/origin/$base" "$tip" 2>/dev/null; then
        echo -e "KEPT\t$b\t#$n is $st; behind $base — rebase before merging"
      else
        echo -e "KEPT\t$b\t#$n is $st"
      fi
    elif [[ -n "$holder" ]]; then
      echo -e "KEPT\t$b\t#$n merged, but the branch is checked out at $holder\tgit checkout $base"
    elif git -C "$REPO_DIR" merge-base --is-ancestor "$tip" "$oid" 2>/dev/null; then
      if [[ "$tip" == "$oid" ]]; then
        echo -e "DELETABLE\t$b\t#$n merged, and ${tip:0:8} is the head it merged"
      else
        echo -e "DELETABLE\t$b\t#$n merged, and ${tip:0:8} is contained in the merged head ${oid:0:8}"
      fi
    else
      local match after created
      match="$(superseding_force_push "$n" "$tip")"
      if [[ -n "$match" ]]; then
        after="$(jq -r .afterCommit.oid <<< "$match")"
        created="$(jq -r .createdAt <<< "$match")"
        echo -e "DELETABLE\t$b\t#$n merged; ${tip:0:8} was a former head, force-pushed to ${after:0:8} at $created — superseded, not diverged"
      else
        echo -e "KEPT\t$b\t#$n merged, but ${tip:0:8} is not contained in it — it holds commits the squash did not"
      fi
    fi
  done < <(git -C "$REPO_DIR" for-each-ref --format='%(refname:short)' refs/heads/ \
             | grep -v "^$base\$")

  local server_refs sb
  if server_refs="$(quote git -C "$REPO_DIR" ls-remote --heads origin)"; then
    while read -r sb; do
      [[ -n "$sb" && "$sb" != "$base" ]] || continue
      pr_json="$(jq -c --arg b "$sb" 'map(select(.headRefName == $b)) | sort_by(.number) | last // empty' <<< "$prs")"
      [[ -n "$pr_json" ]] || continue
      n=$(jq -r .number <<< "$pr_json"); st=$(jq -r .state <<< "$pr_json")
      [[ "$st" == CLOSED ]] || continue
      echo -e "SERVER_DELETABLE\t$sb\t#$n CLOSED unmerged — the forge still holds the branch"
    done < <(printf '%s\n' "$server_refs" | awk '{print $2}' | sed 's#^refs/heads/##')
  else
    echo -e "UNVERIFIED\tforge\tgit ls-remote unreachable — a closed-unmerged PR's server branch would be invisible here"
  fi
}

# rows: STATUS \t ref \t detail — parsed by status() and prune()
stale_tracking() {
  local out line ref
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

# rows: STATUS \t key \t detail \t remedy — the authority is rsc/test/pre-commit-hook.sh
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

upstream() {
  local current sha
  current="$(git -C "$REPO_DIR" branch --show-current)"
  if [[ -z "$current" ]]; then
    sha="$(git -C "$REPO_DIR" rev-parse --short HEAD)"
    echo -e "OK\tcheckout\tdetached at $sha — no upstream to compare\t"
    return
  fi
  if ! git -C "$REPO_DIR" rev-parse --abbrev-ref "$current@{upstream}" &>/dev/null; then
    echo -e "OK\tcheckout\t$current has no upstream — nothing to compare\t"
    return
  fi
  may_send || { echo -e "UNVERIFIED\tcheckout\tYOGA_NO_SEND=1 refuses this send: git fetch (checkout vs upstream unverified)\t"; return; }
  if ! quiet git -C "$REPO_DIR" fetch --quiet origin "$current"; then
    echo -e "UNVERIFIED\tcheckout\tunreachable — checkout vs upstream unverified\t"
    return
  fi
  if git -C "$REPO_DIR" merge-base --is-ancestor "origin/$current" HEAD 2>/dev/null; then
    if git -C "$REPO_DIR" merge-base --is-ancestor HEAD "origin/$current" 2>/dev/null; then
      echo -e "OK\tcheckout\t$current is level with origin/$current\t"
    else
      echo -e "OK\tcheckout\t$current is ahead of origin/$current — local commits not pushed\t"
    fi
  elif git -C "$REPO_DIR" merge-base --is-ancestor HEAD "origin/$current" 2>/dev/null; then
    echo -e "WRONG\tcheckout\t$current is behind origin/$current — the yoga acting here is older than the branch's own newest\tgit -C $REPO_DIR pull --ff-only"
  else
    echo -e "WRONG\tcheckout\t$current and origin/$current have diverged\treconcile $current with origin/$current yourself"
  fi
}

base_branch() {
  may_send || { echo main; return; }
  (cd "$REPO_DIR" && gh repo view --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null) || echo main
}

status() {
  local refuse_class=0 st key detail remedy
  echo "forge settings — declared: src/main/cli/forge/forge.csv; live: this checkout's remote"
  while IFS=$'\t' read -r st key detail remedy; do
    [[ -z "$st" ]] && continue
    case "$st" in
      OK)         echo "  ✓ $key: $detail" ;;
      DRIFT)      echo "  ✗ $key: $detail"; echo "    → run: $remedy"; refuse_class=1 ;;
      UNVERIFIED) echo "  ✗ $key: $detail"; refuse_class=1 ;;
      *)          echo "  – $key: $detail" ;;
    esac
  done < <(reconcile)

  local rows
  rows="$(branches)" || return 1
  if [[ -n "$rows" ]]; then
    echo "branches — what the forge says about each"
    local d=""
    while IFS=$'\t' read -r st key detail remedy; do
      [[ -z "$st" ]] && continue
      case "$st" in
        DELETABLE|SERVER_DELETABLE) echo "  – $key: $detail"; d=1 ;;
        UNVERIFIED)                 echo "  ✗ $key: $detail"; refuse_class=1 ;;
        *)                          echo "  – $key: $detail" ;;
      esac
      [[ -z "$remedy" ]] || echo "    → run: $remedy   # then it is deletable"
    done <<< "$rows"
    [[ -z "$d" ]] || echo "    → run: yoga forge prune"
  fi

  local stale
  stale="$(stale_tracking)" || return 1
  if [[ -n "$stale" ]]; then
    echo "remote-tracking refs — branches the forge has deleted"
    local any=""
    while IFS=$'\t' read -r st key detail; do
      [[ -z "$st" ]] && continue
      case "$st" in
        STALE)      echo "  – $key: $detail"; any=1 ;;
        UNVERIFIED) echo "  ✗ $key: $detail"; refuse_class=1 ;;
        *)          echo "  – $key: $detail" ;;
      esac
    done <<< "$stale"
    [[ -z "$any" ]] || echo "    → run: yoga forge prune"
  fi

  echo "this checkout's gate, and this checkout against its own upstream"
  while IFS=$'\t' read -r st key detail remedy; do
    [[ -z "$st" ]] && continue
    if [[ "$st" == OK ]]; then
      echo "  ✓ $key: $detail"
    else
      echo "  ✗ $key: $detail"; echo "    → run: $remedy"; refuse_class=1
    fi
  done < <(gate; upstream)
  return "$refuse_class"
}

prune() {
  local apply="" st key detail n=0 unverified=""
  [[ "${1-}" == "--apply" ]] && apply=1
  while IFS=$'\t' read -r st key detail; do
    case "$st" in
      UNVERIFIED) unverified=1; continue ;;
      DELETABLE)
        n=$((n + 1))
        if [[ -n "$apply" ]]; then
          enact git -C "$REPO_DIR" branch -D "$key" >/dev/null && echo "deleted $key — $detail"
        else
          echo "would delete $key — $detail"
        fi
        ;;
      SERVER_DELETABLE)
        n=$((n + 1))
        if [[ -n "$apply" ]]; then
          if assert_may_send "git push origin --delete $key (forge prune --apply)"; then
            enact git -C "$REPO_DIR" push origin --delete "$key" \
              && echo "deleted $key on the forge — $detail; evidence-safe: the PR keeps its commits and diff, the reasoning lives in its thread"
          fi
        else
          echo "would delete $key on the forge — $detail; evidence-safe: the PR keeps its commits and diff, the reasoning lives in its thread"
        fi
        ;;
      *) continue ;;
    esac
  done < <(branches)
  local stale_rows ref
  stale_rows="$(stale_tracking)"
  while IFS=$'\t' read -r st ref _; do
    if [[ "$st" == UNVERIFIED ]]; then unverified=1; continue; fi
    [[ "$st" == STALE ]] || continue
    n=$((n + 1))
    if [[ -n "$apply" ]]; then
      enact git -C "$REPO_DIR" update-ref -d "refs/remotes/$ref" && echo "forgot $ref — the forge no longer has it"
    else
      echo "would forget $ref — the forge no longer has it"
    fi
  done <<< "$stale_rows"

  if [[ "$n" == 0 && -n "$unverified" ]]; then
    echo 'could not tell — some rows are UNVERIFIED; see yoga forge for what and why'
  elif [[ "$n" == 0 ]]; then
    echo 'nothing to prune — yoga forge says why for each branch it keeps'
  else
    if [[ -z "$apply" ]]; then
      echo "--- $n item(s); nothing removed. Add --apply to remove them"
    fi
    if [[ -n "$unverified" ]]; then
      echo 'some rows are UNVERIFIED; see yoga forge for what and why'
    fi
  fi
}

sync() {
  local apply=""
  [[ "${1-}" == "--apply" ]] && apply=1
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

merge() {
  local pr="${1:?yoga forge merge <pr>}"
  local oid base head mergeable closing landed
  assert_may_send "gh pr view / gh pr merge / git push / git fetch (yoga forge merge)" \
  && read -r base head mergeable closing < <(cd "$REPO_DIR" && query gh pr view "$pr" \
       --json baseRefName,headRefName,mergeable,closingIssuesReferences \
       --jq '[.baseRefName,.headRefName,.mergeable,(.closingIssuesReferences|length)]|@tsv') \
  && [[ "$mergeable" == MERGEABLE ]] \
  && (( closing > 0 )) \
  && status \
  && enact git -C "$REPO_DIR" fetch origin "$base" "$head" \
  && enact git -C "$REPO_DIR" checkout --detach "origin/$head" \
  && enact git -C "$REPO_DIR" rebase "origin/$base" \
  && enact "$REPO_DIR/yoga" test run \
  && enact git -C "$REPO_DIR" push --force-with-lease origin "HEAD:$head" \
  && oid="$(cd "$REPO_DIR" && query gh pr view "$pr" --json headRefOid --jq .headRefOid)" \
  && enact git -C "$REPO_DIR" checkout "$base" \
  && (cd "$REPO_DIR" && enact gh pr merge "$pr" --squash --match-head-commit "$oid") \
  && landed="$(cd "$REPO_DIR" && query gh pr view "$pr" --json mergeCommit --jq .mergeCommit.oid)" \
  && enact git -C "$REPO_DIR" fetch origin \
  && enact git -C "$REPO_DIR" merge --ff-only "$landed" \
  && prune --apply \
  && quote git -C "$REPO_DIR" status
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] || return 0

case "${1-}" in
  '')        status ;;
  sync)      shift; sync "$@" ;;
  prune)     shift; prune "$@" ;;
  merge)     shift; merge "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "yoga forge: unknown argument: $1 (try: yoga forge --help)" >&2; exit 1 ;;
esac
