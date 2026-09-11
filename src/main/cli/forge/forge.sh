#!/usr/bin/env bash
# forge.sh (corpus-yoga forge) — the forge's merge settings, and the operations that obey them.
#
# Usage:
#   corpus-yoga forge                 # declared vs live
#   corpus-yoga forge sync [--apply]  # make the forge agree with src/main/cli/forge/forge.csv
#   corpus-yoga forge merge <pr>      # the reviewer's one act (#483): refuse, relocate if the base moved, stand at the head and run the data gate, flip the body, squash, converge
#   corpus-yoga forge prune [--apply] # forget what the forge no longer has
#   corpus-yoga forge capture [--to <dir>] # deposit the forge's ledger under data/input/github/forge/gh-CLI/<stamp>/ - nothing, if unchanged

set -euo pipefail

SELF='src/main/cli/forge/forge.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
DECLARED="$REPO_DIR/src/main/cli/forge/forge.csv"
# shellcheck source=src/main/send.sh
source "$REPO_DIR/src/main/send.sh"
# shellcheck source=src/main/enact.sh
source "$REPO_DIR/src/main/enact.sh"
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_DIR/src/main/cli/parse_argv.sh"

# rows: STATUS \t key \t detail \t remedy — parsed by status() and `corpus-yoga prerequisites`
reconcile() {
  [[ -f "$DECLARED" ]] || { echo -e "UNVERIFIED\tforge.csv\tno src/main/cli/forge/forge.csv — nothing declared\t"; return; }
  command -v gh &>/dev/null || { echo -e "UNVERIFIED\tgh\tgh not found (install: brew install gh)\t"; return; }
  may_send || { echo -e "UNVERIFIED\tforge\tYOGA_NO_SEND=1 refuses this send: gh api (live settings unread)\t"; return; }
  local live
  if ! live="$(cd "$REPO_DIR" && gh api "repos/{owner}/{repo}" 2>/dev/null)"; then
    echo -e "UNVERIFIED\tforge\tunreachable (offline, no GitHub remote, or: gh auth login)\t"
    return
  fi
  printf '%s' "$live" | "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/forge/reconcile.py" "$DECLARED" 2>/dev/null \
    || echo -e "UNVERIFIED\tforge.csv\tunreadable, malformed, or no venv (src/run_python_script.sh refused)\t"
  # This checkout's origin against the repository the forge answers for it (#579). After a
  # rename the forge redirects, so its full_name is the current name while origin may still
  # spell the old one: every push is redirected and works, and a reader opened from the old
  # name misses this checkout's PRs. MOVED, not DRIFT: a redirected origin refuses nothing.
  local origin_url canonical named remedy_url
  origin_url="$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)"
  canonical="$(jq -r '.full_name // empty' <<< "$live")"
  named="$(sed -E 's#^(https?://[^/]+/|git@[^:]+:|ssh://git@[^/]+/)##; s#\.git$##; s#/$##' <<< "$origin_url")"
  if [[ -z "$origin_url" || -z "$canonical" ]]; then
    echo -e "UNVERIFIED\torigin\tno origin URL, or the forge's answer carries no full_name\t"
  elif [[ "$named" == "$canonical" ]]; then
    echo -e "OK\torigin\t$origin_url names $canonical, the repository the forge answers for it\t"
  else
    case "$origin_url" in
      git@*|ssh://*) remedy_url="$(jq -r .ssh_url <<< "$live")" ;;
      *)             remedy_url="$(jq -r .clone_url <<< "$live")" ;;
    esac
    echo -e "MOVED\torigin\t$origin_url names $named, but the forge answers for $canonical - renamed; pushes are redirected, and a reader opened from the old name misses this checkout's PRs\tgit remote set-url origin $remedy_url"
  fi
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
    echo -e "WRONG\tpre-commit\tnot the accepted hook — commits from here are not being vetted\tcorpus-yoga test install-hook"
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
    echo -e "WRONG\tcheckout\t$current is behind origin/$current — the corpus-yoga acting here is older than the branch's own newest\tgit -C $REPO_DIR pull --ff-only"
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
      MOVED)      echo "  – $key: $detail"; echo "    → run: $remedy" ;;
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
    [[ -z "$d" ]] || echo "    → run: corpus-yoga forge prune"
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
    [[ -z "$any" ]] || echo "    → run: corpus-yoga forge prune"
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
    echo 'could not tell — some rows are UNVERIFIED; see corpus-yoga forge for what and why'
  elif [[ "$n" == 0 ]]; then
    echo 'nothing to prune — corpus-yoga forge says why for each branch it keeps'
  else
    if [[ -z "$apply" ]]; then
      echo "--- $n item(s); nothing removed. Add --apply to remove them"
    fi
    if [[ -n "$unverified" ]]; then
      echo 'some rows are UNVERIFIED; see corpus-yoga forge for what and why'
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
      (cd "$REPO_DIR" && eval "$remedy" >/dev/null) || { echo "corpus-yoga forge sync: $key failed — settings unchanged for it" >&2; exit 1; }
    else
      echo "  would run: $remedy"
    fi
  done <<< "$rows"
  if [[ "$drift" == 0 ]]; then
    if ! printf '%s\n' "$rows" | grep -q $'^OK\t'; then
      echo "corpus-yoga forge sync: the live settings could not be read — nothing verified, nothing to agree" >&2
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

# The merge is the reviewer's one act (#483): every refusal (OPEN, an aims-to-
# complete body, the title copy #479, the blockers #482, refuse-class drift),
# the relocation only if the base moved (the lifetime's one rebase, replaying only
# the commits the base does not already hold, tree for tree - #585; rsc/test/
# conflicts are CONTRIBUTING's syntactic class, taken wholesale and re-derived;
# any other conflict aborts to review), the held checkout resynced, the body's
# aims-to-closes as the LAST edit before the squash - and a failed squash
# un-flips the body, leaving the world as found, so a flipped-but-unmerged PR
# cannot exist. No squash, reword or amend exists below: commits cannot come to
# carry the parser's words through this command. The chain is teed into one run
# log; PIPESTATUS carries the verdict past the tee, so the pipe launders nothing.
merge() {
  local pr="$1"
  local stamp log rc
  stamp="$(date -u '+%Y-%m-%dT%H%M%SZ')"
  mkdir -p "$REPO_DIR/tmp/logs/forge/merge"
  log="$REPO_DIR/tmp/logs/forge/merge/$stamp.log"
  { echo "forge merge — $stamp · room: $(cat "$REPO_DIR/machine-name.txt" 2>/dev/null || echo '(unbound)') · $(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null)"
    echo "corpus-yoga forge merge $pr"
    merge_chain "$pr"
  } 2>&1 | tee "$log"
  rc="${PIPESTATUS[0]}"
  echo "Log: $log"
  return "$rc"
}

# The PR that introduced a base commit - exact for a squash on the default branch
# (repos/{owner}/{repo}/commits/<sha>/pulls). Empty when the send is refused or the
# forge unreachable.
pr_of_commit() {  # <sha>
  may_send || return 0
  (cd "$REPO_DIR" && quote gh api "repos/{owner}/{repo}/commits/$1/pulls" --jq '.[0].number // empty') || true
}

# The heads a merged PR held before each relocation (#585): the force-push
# timeline's beforeCommits (src/main/cli/forge/superseded-heads.graphql). A stacked
# branch built on the parent before the forge relocated it carries one of these.
# Empty when the send is refused or the forge unreachable.
pr_former_heads() {  # <pr-number>
  may_send || return 0
  (cd "$REPO_DIR" && quote gh api graphql -F owner='{owner}' -F repo='{repo}' -F number="$1" \
      -F query=@src/main/cli/forge/superseded-heads.graphql \
      --jq '.data.repository.pullRequest.timelineItems.nodes[].beforeCommit.oid') || true
}

# A merged PR's final head - the one its squash was pinned to.
pr_final_head() {  # <pr-number>
  may_send || return 0
  (cd "$REPO_DIR" && quote gh pr view "$1" --json headRefOid --jq .headRefOid) || true
}

# One patch-id per commit of a range, rsc/test/ aside (the settle regenerates it);
# a commit touching nothing else yields an empty line.
patch_ids() {  # <range>
  local sha
  for sha in $(git -C "$REPO_DIR" rev-list "$1"); do
    git -C "$REPO_DIR" show "$sha" --format= -- . ':!rsc/test' | git patch-id --stable | cut -d' ' -f1
    echo
  done | awk 'NF' | sort -u
}

# Whether git vouches for skipping everything up to a former head (#585): the PR's
# final head has the tree of a base commit (its squash is that head), and every
# commit the skip drops has a patch twin among the final head's commits since the
# merge-base - a relocation the forge made, not a rewrite that dropped content the
# branch stands on. What gh nominates, git confirms; a candidate git cannot vouch
# for is refused by name and the search goes on.
skip_vouched() {  # <merge-base> <former> <final> <base-trees>
  local merge_base="$1" former="$2" final="$3" base_trees="$4" final_tree merged_ids id
  final_tree="$(git -C "$REPO_DIR" rev-parse "$final^{tree}" 2>/dev/null)" || { echo "  candidate ${former:0:7}: final head ${final:0:7} unknown to this repository" >&2; return 1; }
  grep -q " $final_tree\$" <<< "$base_trees" || { echo "  candidate ${former:0:7}: the merged head ${final:0:7} has no base commit's tree" >&2; return 1; }
  merged_ids="$(patch_ids "$merge_base..$final")"
  for id in $(patch_ids "$merge_base..$former"); do
    grep -qx "$id" <<< "$merged_ids" || { echo "  candidate ${former:0:7}: a commit it would skip has no patch twin in the merged head ${final:0:7}" >&2; return 1; }
  done
}

# The point a branch relocates from (#585): the newest of its commits since the
# merge-base that the base already holds - else the merge-base itself, the plain
# rebase. Held is read two ways. Tree for tree: a parent merged with the base unmoved
# keeps its head's TREE in its squash though not its patches (a one-commit parent
# squashes to its own patch and git drops it unasked; a two-commit parent squashes to
# a patch matching neither, and a plain rebase replays both onto their own squash).
# By name: a parent the forge relocated before its squash keeps none of the child's
# trees, but the forge holds its former heads - the newest one the branch carries,
# and git vouches for (skip_vouched), is the point. gh nominates, git decides.
# Prints "<onto> <commits held> <own commits to replay> <merged PR or ->".
relocation_point() {  # <base-ref> <head-ref>
  local base_ref="$1" head_ref="$2" merge_base onto="" named="" sha tree base_trees pr final former count best=-1
  merge_base="$(git -C "$REPO_DIR" merge-base "$base_ref" "$head_ref")" || return 1
  base_trees="$(git -C "$REPO_DIR" log --format='%H %T' "$merge_base..$base_ref")"
  while read -r sha tree; do
    if grep -q " $tree\$" <<< "$base_trees"; then
      onto="$sha"; named="$(pr_of_commit "$(grep " $tree\$" <<< "$base_trees" | head -1 | cut -d' ' -f1)" || true)"
      break
    fi
  done < <(git -C "$REPO_DIR" log --format='%H %T' "$merge_base..$head_ref")
  if [[ -z "$onto" ]]; then
    for sha in $(git -C "$REPO_DIR" rev-list "$merge_base..$base_ref"); do
      pr="$(pr_of_commit "$sha" || true)"; [[ -n "$pr" ]] || continue
      final="$(pr_final_head "$pr" || true)"; [[ -n "$final" ]] || continue
      for former in $(pr_former_heads "$pr" || true); do
        git -C "$REPO_DIR" merge-base --is-ancestor "$merge_base" "$former" 2>/dev/null || continue
        git -C "$REPO_DIR" merge-base --is-ancestor "$former" "$head_ref" 2>/dev/null || continue
        skip_vouched "$merge_base" "$former" "$final" "$base_trees" || continue
        count="$(git -C "$REPO_DIR" rev-list --count "$merge_base..$former")"
        if (( count > best )); then best=$count; onto="$former"; named="$pr"; fi
      done
    done
  fi
  [[ -n "$onto" ]] || onto="$merge_base"
  echo "$onto $(git -C "$REPO_DIR" rev-list --count "$merge_base..$onto") $(git -C "$REPO_DIR" rev-list --count "$onto..$head_ref") ${named:--}"
}

# The relocation of a moved base (#507, #585): in a detached worktree of its own
# under tmp/forge/merge/, never in the invoking checkout - so a halt or an
# interruption leaves the checkout as found. Replays only the branch's own commits
# (relocation_point), takes an rsc/test/ conflict wholesale (the syntactic class,
# CONTRIBUTING.md), settles the artifacts by the gate's own regeneration, commits
# that if anything changed, pushes leased against <old-sha>, and disposes of the
# worktree whatever happened. Prints the relocated head on success; every halt
# prints its own last line and returns 1.
relocated() {  # <base> <head> <old-sha>
  local base="$1" head="$2" old_sha="$3"
  local wt onto held own merged_pr conflicted guard=0 oid
  wt="$REPO_DIR/tmp/forge/merge/$(date -u '+%Y-%m-%dT%H%M%SZ')-$head"
  dispose() {
    git -C "$REPO_DIR" worktree remove --force "$wt" >/dev/null 2>&1 || true
    git -C "$REPO_DIR" worktree prune >/dev/null 2>&1 || true
  }
  mkdir -p "$REPO_DIR/tmp/forge/merge"
  enact git -C "$REPO_DIR" worktree add --detach "$wt" "refs/remotes/origin/$head" >&2 \
    || { echo "relocation halted — could not open a worktree at origin/$head" >&2; return 1; }
  # A paused rebase is an EXPECTED state, not a failure (#485): the attempt
  # face relays no verdict, git's advice channels are off, and the narration
  # below names the state in the mechanism's own voice.
  read -r onto held own merged_pr < <(relocation_point "refs/remotes/origin/$base" "refs/remotes/origin/$head") || true
  if [[ -z "$onto" ]]; then
    echo "relocation halted — no relocation point: origin/$base and origin/$head share no merge-base" >&2
    dispose; return 1
  fi
  [[ "$merged_pr" != - ]] || merged_pr=""
  if (( held > 0 )); then
    echo "relocating in $wt: $held commit(s) up to ${onto:0:7} already stand on origin/$base${merged_pr:+ - the head of #$merged_pr, merged}; replaying the $own own commit(s) from there" >&2
  else
    echo "relocating in $wt: replaying $own commit(s) from the merge-base ${onto:0:7}" >&2
  fi
  if ! attempt git -C "$wt" -c advice.mergeConflict=false -c advice.resolveConflict=false rebase --onto "refs/remotes/origin/$base" "$onto" >&2; then
    echo "rebase paused on conflicts — classifying against the syntactic rule (CONTRIBUTING.md)" >&2
    while [[ -d "$(git -C "$wt" rev-parse --git-path rebase-merge)" ]]; do
      guard=$((guard + 1))
      if (( guard > 50 )); then
        enact git -C "$wt" rebase --abort >&2
        echo "relocation halted — the rebase did not converge in 50 steps; resolve in review" >&2
        dispose; return 1
      fi
      conflicted="$(git -C "$wt" diff --name-only --diff-filter=U)"
      if grep -qv '^rsc/test/' <<< "$conflicted"; then
        echo "conflict outside rsc/test/ — the syntactic rule does not apply:" >&2
        grep -v '^rsc/test/' <<< "$conflicted" | sed 's/^/  /' >&2
        enact git -C "$wt" rebase --abort >&2
        echo "relocation halted — a real conflict lands in the source; resolve it in review, not in the merge" >&2
        dispose; return 1
      fi
      if [[ -n "$conflicted" ]]; then
        echo "conflict confined to rsc/test/ — the syntactic class, taken wholesale" >&2
        enact git -C "$wt" checkout --theirs rsc/test/ >&2 || { dispose; return 1; }
        enact git -C "$wt" add rsc/test/ >&2 || { dispose; return 1; }
      fi
      GIT_EDITOR=true attempt git -C "$wt" -c advice.mergeConflict=false rebase --continue >&2 || true
    done
  fi
  # The worktree is a fresh tree: the machine-local parsers (src/gen, #597) are
  # generated there before the gate needs them, and the settle runs FROM there -
  # src/test/dev/run.sh gates the tree the current directory belongs to.
  (cd "$wt" && quiet "$wt/corpus-yoga" grammar sync) >&2 \
    || echo "the parsers could not be generated in the worktree - the settle below will say what it lacks" >&2
  (cd "$wt" && quiet "$wt/src/test/dev/run.sh" --settle) >&2 \
    || { echo "relocation halted — the settle run failed; a red check on the relocated head is a real failure" >&2; dispose; return 1; }
  if [[ -n "$(git -C "$wt" status --porcelain rsc/test/)" ]]; then
    if ! enact git -C "$wt" add rsc/test/ >&2 \
       || ! enact git -C "$wt" commit -m "regenerated artifacts settle on the relocated base" >&2; then
      echo "relocation halted — the settle commit failed; the gate's veto above says why" >&2
      dispose; return 1
    fi
  fi
  enact git -C "$wt" push --force-with-lease="refs/heads/$head:$old_sha" origin "HEAD:refs/heads/$head" >&2 \
    || { echo "relocation halted — the lease refused; the branch moved under the merge" >&2; dispose; return 1; }
  oid="$(git -C "$wt" rev-parse HEAD)"
  dispose
  echo "$oid"
}

merge_chain() {
  local pr="$1"
  local state base head body branch_here old_sha flipped n moved=0
  local oid landed
  assert_may_send "gh pr view / gh issue view / gh api / gh pr edit / gh pr merge / git fetch / git push (corpus-yoga forge merge)"     || { echo "forge merge: NOT DONE — sends refused (YOGA_NO_SEND)"; return 1; }
  read -r state base head < <(cd "$REPO_DIR" && query gh pr view "$pr"        --json state,baseRefName,headRefName --jq '[.state,.baseRefName,.headRefName]|@tsv')     || { echo "forge merge: NOT DONE — the PR read failed; does $pr name a PR?"; return 1; }
  [[ "$state" == OPEN ]]     || { echo "forge merge: NOT DONE — #$pr is $state; only an open PR merges"; return 1; }
  body="$(cd "$REPO_DIR" && quote gh pr view "$pr" --json body --jq .body)"     || { echo "forge merge: NOT DONE — the body read failed"; return 1; }
  grep -Eq 'aims to complete #[0-9]+' <<< "$body"     || { echo "forge merge: NOT DONE — the body carries no 'aims to complete #N' to flip"; return 1; }
  # The title is a verbatim COPY of the title of an issue the body aims to
  # complete (#479): the should's one home is the issue, main's subject becomes
  # the disposed should, and a non-copy refuses HERE, before any enacting step.
  local aimed title issue_number issue_title copied=0
  aimed="$(grep -oE 'aims to complete #[0-9]+' <<< "$body" | grep -oE '[0-9]+' | sort -u)"
  title="$(cd "$REPO_DIR" && quote gh pr view "$pr" --json title --jq .title)"     || { echo "forge merge: NOT DONE — the title read failed"; return 1; }
  while read -r issue_number; do
    [[ -n "$issue_number" ]] || continue
    issue_title="$(cd "$REPO_DIR" && quote gh issue view "$issue_number" --json title --jq .title)" || continue
    [[ "$title" == "$issue_title" ]] && copied=1
  done <<< "$aimed"
  [[ "$copied" == 1 ]]     || { echo "forge merge: NOT DONE — the title copies no issue the body aims to complete (#479); retitle the PR as the verbatim copy of the central issue's title"; return 1; }
  # Every aimed issue's OPEN blockers must be aimed too (#482): closing a
  # blocked issue with its stated precondition unmet is what blocked_by
  # exists to prevent, and the refusal lands here, before any enacting step.
  local blocker_rows blocker_number blocker_state
  while read -r issue_number; do
    [[ -n "$issue_number" ]] || continue
    blocker_rows="$(cd "$REPO_DIR" && quote gh api "repos/{owner}/{repo}/issues/$issue_number/dependencies/blocked_by" --jq '.[] | [.number, .state] | @tsv')" || continue
    while IFS=$'\t' read -r blocker_number blocker_state; do
      [[ -n "$blocker_number" ]] || continue
      [[ "$blocker_state" == "closed" ]] && continue
      grep -qx "$blocker_number" <<< "$aimed"       || { echo "forge merge: NOT DONE — #$issue_number is blocked by open #$blocker_number, which this body does not aim to complete (#482)"; return 1; }
    done <<< "$blocker_rows"
  done <<< "$aimed"
  status     || { echo "forge merge: NOT DONE — refuse-class drift; the standing report above names it"; return 1; }
  enact git -C "$REPO_DIR" fetch origin "$base" "$head"     || { echo "forge merge: NOT DONE — the fetch failed"; return 1; }
  branch_here="$(git -C "$REPO_DIR" branch --show-current)"
  if [[ "$branch_here" == "$head" ]]; then
    [[ -z "$(git -C "$REPO_DIR" status --porcelain)" ]]       || { echo "forge merge: NOT DONE — this checkout holds $head with a dirty tree; commit or stash first, never reset"; return 1; }
    git -C "$REPO_DIR" merge-base --is-ancestor "refs/heads/$head" "refs/remotes/origin/$head" 2>/dev/null       || { echo "forge merge: NOT DONE — local $head holds commits origin/$head does not; push them first"; return 1; }
  fi
  # The squash pin is the merge's OWN sha (#488): the head fetched here, or the
  # head the relocation pushes below - never a PR-API re-read, which is
  # eventually consistent and served the pre-push sha in the same breath as the
  # push (the two failed merges of PR #486, 2026-08-14, this room's logs).
  oid="$(git -C "$REPO_DIR" rev-parse "refs/remotes/origin/$head")"
  if git -C "$REPO_DIR" merge-base --is-ancestor "refs/remotes/origin/$base" "refs/remotes/origin/$head" 2>/dev/null; then
    echo "base unmoved — origin/$head already stands on origin/$base; nothing to relocate"
  else
    old_sha="$(git -C "$REPO_DIR" ls-remote origin "refs/heads/$head" | cut -f1)"
    [[ -n "$old_sha" ]] || { echo "forge merge: NOT DONE — origin has no refs/heads/$head to lease against"; return 1; }
    oid="$(relocated "$base" "$head" "$old_sha")" || { echo "forge merge: NOT DONE — the relocation halted; its last line above names where"; return 1; }
    moved=1
    if [[ "$branch_here" == "$head" ]]; then
      if ! enact git -C "$REPO_DIR" checkout "$head" \
         || ! enact git -C "$REPO_DIR" reset --hard "refs/remotes/origin/$head"; then
        echo "forge merge: NOT DONE — the resync failed; origin/$head is the relocated copy, this checkout's $head is not"
        return 1
      fi
      echo "resynced this checkout: $head is the relocated copy of what was reviewed"
    fi
  fi
  # The data gate (#541, #549): corpus-yoga pipeline run at the head being merged.
  # The merge stands there itself - detached at the exact sha - and puts the
  # checkout back where it was if the gate is red.
  local was
  was="$(git -C "$REPO_DIR" branch --show-current)"
  [[ -n "$was" ]] || was="$(git -C "$REPO_DIR" rev-parse HEAD)"
  restore() { enact git -C "$REPO_DIR" checkout "$was" >/dev/null 2>&1 || true; }
  if [[ "$(git -C "$REPO_DIR" rev-parse HEAD)" != "$oid" ]]; then
    enact git -C "$REPO_DIR" checkout --detach "$oid"       || { echo "forge merge: NOT DONE — could not check out ${oid:0:8}"; return 1; }
  fi
  # The run streams to the terminal as it happens and writes its own log; this
  # log keeps its verdict lines only (from the usr gate line to the end), so the
  # run is recorded once (#547 review, 2026-08-25). No terminal: nothing to stream.
  local gate_rc=0 live=/dev/null verdict stages
  { : > /dev/tty; } 2>/dev/null && live=/dev/tty
  verdict="$(mktemp)"
  echo "enact: $REPO_DIR/src/main/cli/pipeline/pipeline.sh run" >&2
  # Under errexit a red pipeline would end the merge here, verdict unwritten (#601):
  # the run's status is read from the pipeline, never let veto the line.
  set +e
  "$REPO_DIR/src/main/cli/pipeline/pipeline.sh" run 2>&1 | tee "$live" | awk '/^usr gate:/ { p = 1 } p' | tee "$verdict"
  gate_rc=${PIPESTATUS[0]}
  set -e
  stages="$(awk '/failing stage\(s\):/ { p = 1; next } p && /^  [^ ]/ { printf "%s ", $1 } p && !/^  / { exit }' "$verdict")"
  rm -f "$verdict"
  # The gate regenerates rsc/test/ where the branch's committed artifacts are stale;
  # those files are derived, so the halt discards them and puts the checkout back
  # (#507): the finding is stated below, the checkout stands as found.
  put_back() {
    enact git -C "$REPO_DIR" checkout -- rsc/test/ >/dev/null 2>&1 || true
    restore
    [[ "$(git -C "$REPO_DIR" branch --show-current 2>/dev/null || git -C "$REPO_DIR" rev-parse HEAD)" == "$was" ]] \
      || echo "the checkout did NOT come back to $was — put it back by hand: git checkout $was"
  }
  if [[ "$gate_rc" -ne 0 ]]; then
    put_back
    echo "forge merge: NOT DONE — data gate red at ${oid:0:8}: usr gate FAIL, failing stage(s) ${stages:-unstated} (the run's own log names the findings); checkout restored to $was"
    return 1
  fi
  if [[ -n "$(git -C "$REPO_DIR" status --porcelain)" ]]; then
    put_back
    echo "forge merge: NOT DONE — data gate green at ${oid:0:8} but it left rsc/test/ changed: the branch's committed artifacts are stale; run corpus-yoga test run on it and push; checkout restored to $was"
    return 1
  fi
  echo "data gate: green at ${oid:0:8}"
  n="$(grep -Ec 'aims to complete #[0-9]+' <<< "$body")"
  flipped="$("$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/forge/flip.py" <<< "$body")"
  printf '%s' "$flipped" | (cd "$REPO_DIR" && enact gh pr edit "$pr" --body-file -)     || { echo "forge merge: NOT DONE — the flip failed; the body still aims, nothing merged$([[ $moved == 1 ]] && echo ' (the relocation stands)')"; return 1; }
  # The squash is pinned to the head every check above saw; between the flip
  # and here the closes phrasing exists for an instant, and a refused squash
  # restores the body as found (#483).
  if ! (cd "$REPO_DIR" && enact gh pr merge "$pr" --squash --match-head-commit "$oid"); then
    if printf '%s' "$body" | (cd "$REPO_DIR" && enact gh pr edit "$pr" --body-file -); then
      echo "the body is restored as found — it aims again, nothing closed"
    else
      echo "FAIL: the restore failed too - the body says closes on an unmerged PR; edit it by hand"
    fi
    echo "forge merge: NOT DONE — the squash refused; nothing merged"
    return 1
  fi
  landed="$(cd "$REPO_DIR" && query gh pr view "$pr" --json mergeCommit --jq .mergeCommit.oid)"     || { echo "forge merge: NOT DONE — merged, but the merge commit read failed; converge by hand: git fetch origin && git merge --ff-only"; return 1; }
  if ! enact git -C "$REPO_DIR" checkout "$base"     || ! enact git -C "$REPO_DIR" fetch origin     || ! enact git -C "$REPO_DIR" merge --ff-only "$landed"     || ! prune --apply     || ! quote git -C "$REPO_DIR" status; then
    echo "forge merge: NOT DONE — merged as ${landed:0:8}, but this checkout did not converge; the last NOT-done line above names where"
    return 1
  fi
  echo "forge merge: DONE — #$pr squashed as ${landed:0:8} ($n should(s) closed); this checkout converged on it"
}

# The capture is src/main/cli/forge/capture.py's; this face only stamps the deposit.
# The run log (room, head, every gh command, the verdict) is the launcher's tee, as
# for every verb declaring sends or w (cli.py _log_enacting, #453).
capture() {
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/forge/capture.py" "$(date -u '+%Y-%m-%dT%H%M%SZ')" "$@"
}

[[ "${BASH_SOURCE[0]}" == "${0}" ]] || return 0

case "${1-}" in
  '')        status ;;
  sync)      shift; parse_argv forge sync "$@"; sync "$@" ;;
  prune)     shift; parse_argv forge prune "$@"; prune "$@" ;;
  merge)     shift; parse_argv forge merge "$@"; merge "$@" ;;
  capture)   shift; parse_argv forge capture "$@"; capture "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "corpus-yoga forge: unknown argument: $1 (try: corpus-yoga forge --help)" >&2; exit 1 ;;
esac
