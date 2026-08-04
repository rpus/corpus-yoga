#!/usr/bin/env bash
# forge.sh (yoga forge) — the forge's merge settings, and the operations that obey them.
#
# The settings decide how main's history is composed and live on the SERVER, where no clone
# sees them and no git config holds them; src/main/cli/forge/forge.csv declares them.
#
# Usage:
#   yoga forge                 # declared vs live
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
# shellcheck source=src/main/enact.sh
source "$REPO_DIR/src/main/enact.sh"  # enact — echo/execute/trap/relay (#275)

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

# A former head the forge's own record proves superseded (#286): sha-containment fails
# for a rebase orphan exactly as it does for genuine divergence, but a force-push event
# on the merged PR itself is the forge's proof the two are not the same defect. $tip
# ancestor-or-equal of a recorded beforeCommit means the push that replaced it is on
# the record, named here rather than assumed; a tip the record cannot vouch for is left
# to the caller to report as KEPT.
superseding_force_push() {  # <pr-number> <tip>
  local n="$1" tip="$2" events event before
  # shellcheck disable=SC2016  # $owner/$repo/$number are GraphQL variables, not bash expansion
  events="$(quiet gh api graphql -F owner='{owner}' -F repo='{repo}' -F number="$n" -f query='
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          timelineItems(first: 100, itemTypes: [HEAD_REF_FORCE_PUSHED_EVENT]) {
            nodes { ... on HeadRefForcePushedEvent { createdAt beforeCommit { oid } afterCommit { oid } } }
          }
        }
      }
    }' --jq '.data.repository.pullRequest.timelineItems.nodes[]')" || return 0
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

# rows: STATUS \t branch \t detail — every branch the forge knows of, local or
# server-only, and what it says about each. Discovery runs branch → PR, not PR →
# branch: a branch you had forgotten is exactly the one whose PR number you cannot
# recall, so a listing keyed on the PR is unreachable when it is needed. One
# `gh pr list` indexes every PR by its head branch; per-branch queries would cost a
# round trip each to answer the same question.
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
        echo -e "KEPT\t$b\t#$n is CLOSED, but the branch is checked out at $holder\tgit checkout $base"
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
      echo -e "KEPT\t$b\t#$n merged, but the branch is checked out at $holder\tgit checkout $base"
    elif git -C "$REPO_DIR" merge-base --is-ancestor "$tip" "$oid" 2>/dev/null; then
      echo -e "DELETABLE\t$b\t#$n merged, and ${tip:0:8} is contained in the merged head ${oid:0:8}"
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

  # Server-only residue (#285): a branch the forge still holds for a PR it closed
  # WITHOUT merging. delete_branch_on_merge fires only on merge, so this branch has no
  # local trace and, until now, no report — invisible to every broom prune ever swung.
  # The server leaving is the forge's own fact, independent of any checkout: reported
  # whether or not a local branch of the same name exists. A surviving local branch
  # gets its own row from the loop above — two residues, two rows, both honest.
  local server_refs sb
  if server_refs="$(quiet git -C "$REPO_DIR" ls-remote --heads origin)"; then
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

# The ✗ classes are not alike (#142): REFUSE-class means the merge would land badly
# (settings drift — the squash under undeclared rules; a wrong hook — unvetted work);
# TIDY-class means this checkout's bookkeeping is behind (a stale tracking ref, a
# deletable merged branch) — a chore the merge's own tidy-up clears, never a danger.
# status renders both identically (a ✗ is a ✗); the difference is who may proceed:
# merge refuses only on refuse-class and says so for tidy. The classification is
# carried in these two variables, set as the rows render — one derivation, one pass.
STATUS_REFUSE=0
STATUS_TIDY=0

status() {
  echo "forge settings — declared: src/main/cli/forge/forge.csv; live: this checkout's remote"
  STATUS_REFUSE=0; STATUS_TIDY=0
  local st key detail remedy drift=0
  while IFS=$'\t' read -r st key detail remedy; do
    [[ -z "$st" ]] && continue
    case "$st" in
      OK)    echo "  ✓ $key: $detail" ;;
      DRIFT) echo "  ✗ $key: $detail"; echo "    → run: $remedy"; drift=1; STATUS_REFUSE=1 ;;
      *)     echo "  – $key: $detail" ;;
    esac
  done < <(reconcile)

  # The branches the forge knows of — local, and server-only residue it created itself
  # (#285, #286). A merged branch surviving here is drift of the same kind as a forge
  # setting that disagrees with src/main/cli/forge/forge.csv: reconcilable state, and
  # this is where it is named.
  local rows
  rows="$(branches)"
  if [[ -n "$rows" ]]; then
    echo "branches — what the forge says about each"
    # A row that names a remedy prints it, whatever its status: a branch KEPT because you
    # are standing on it is the one state the reader cannot leave by reading — every other
    # row here either needs nothing or is covered by the prune line below.
    local d remedy
    while IFS=$'\t' read -r st key detail remedy; do
      [[ -z "$st" ]] && continue
      case "$st" in
        DELETABLE|SERVER_DELETABLE) echo "  ✗ $key: $detail"; d=1; STATUS_TIDY=1 ;;
        *)                          echo "  – $key: $detail" ;;
      esac
      [[ -z "$remedy" ]] || echo "    → run: $remedy   # then it is deletable"
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
        STALE) echo "  ✗ $key: $detail"; any=1; STATUS_TIDY=1 ;;
        *)     echo "  – $key: $detail" ;;
      esac
    done <<< "$stale"
    [[ -z "$any" ]] || echo "    → run: yoga forge prune"
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
      echo "  ✗ $key: $detail"; echo "    → run: $remedy"; drift=1; STATUS_REFUSE=1
    fi
  done < <(gate)
  # the exit carries the REFUSE class only: tidy-class ✗s inform and prescribe but do
  # not fail the status — the same location-decoupling as prerequisites' exit (severity
  # in the rows; refusal at the acts, and only for what would land badly)
  return $((STATUS_REFUSE))
}

# Delete exactly what `branches` marked DELETABLE or SERVER_DELETABLE — one predicate,
# so what is listed and what is removed cannot disagree. Local: a squash makes a merged
# branch look unmerged to git, so `git branch -d` refuses and only -D will do it; the
# safety is the containment (or force-push) test above, never git's opinion. Server
# (#285): a closed-unmerged PR's branch — deletable because the PR keeps its own commits
# and diff on the forge independently of the branch, and the reasoning lives in its
# thread, not in this checkout.
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
          # A send that IS the work — refuse loudly rather than silently skip, per
          # send.sh's assert_may_send contract; the item stays counted and reported,
          # not vanished, so a refusal under YOGA_NO_SEND reads as "not done", never
          # as "nothing to prune" (#285's own requirement, generalised from #200's).
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
# The mechanical half of semver (#136): what happened to the COMMAND SURFACE, derived
# by diffing the declaration tree across the merge — commands and verbs added, removed,
# changed. The JUDGMENT (fracture vs fix) stays human, in the PR's what; this roster is
# the part a reader should never have to compile by eye. Path shape: one dir deep only,
# so the top-level schemas and documents never enter the roster.
surface_roster() {  # <base-ref> <head-oid>
  git -C "$REPO_DIR" diff --name-status "$1...$2" -- 'src/main/cli/*/*.json' 2>/dev/null |   awk -F'	' '{
      n = split($2, seg, "/"); cmd = seg[n-1]; f = seg[n]; sub(/\.json$/, "", f)
      what = (f == cmd) ? "yoga " cmd " (the command)" : "yoga " cmd " " f
      if      ($1 == "A") print "    + " what
      else if ($1 == "D") print "    - " what
      else                print "    ~ " what
    }'
}

# to test should name only commands that exist (#135): the prescriptions discipline
# extended to the PR body's test section — a warning, never a gate over prose. Inline
# backticked spans are stripped first (mentions wear backticks); a second token is
# challenged only when the command HAS declared verbs and the token is not one (a
# command with positional args tolerates anything).
totest_check() {  # stdin: the PR body
  local section cmd verb bad=""
  section="$(awk '/^[[:space:]]*-[[:space:]]*\*?\*?test\*?\*?[[:space:]:—-]/{on=1} on && /^[[:space:]]*-[[:space:]]*\*?\*?(use|do)\*?\*?[[:space:]:—-]/{exit} on{print}')"
  [[ -n "$section" ]] || { echo "  to test: no section found in the body (the template teaches one)"; return 0; }
  # shellcheck disable=SC2016  # the backticks in the sed below are pattern, not expansion
  while read -r cmd verb; do
    [[ -n "$cmd" ]] || continue
    if [[ ! -f "$REPO_DIR/src/main/cli/$cmd/$cmd.json" ]]; then
      bad+="yoga $cmd (no such command) "
    elif [[ -n "$verb" && ! -f "$REPO_DIR/src/main/cli/$cmd/$verb.json" ]]; then
      # challenged only when the command has verbs at all
      local f has_verbs=""
      for f in "$REPO_DIR/src/main/cli/$cmd/"*.json; do
        [[ "$(basename "$f")" == "$cmd.json" ]] || { has_verbs=1; break; }
      done
      [[ -z "$has_verbs" ]] || bad+="yoga $cmd $verb (no such verb) "
    fi
  done < <(printf '%s\n' "$section" | sed 's/`[^`]*`//g' \
           | grep -oE 'yoga [a-z][a-z-]*( [a-z][a-z-]*)?' | sort -u \
           | awk '{print $2, $3}')
  if [[ -n "$bad" ]]; then
    echo "  ⚠ to test names commands the surface lacks: $bad"
  else
    echo "  to test: every named command is on the surface"
  fi
}

# One envelope verdict (#266): every refusal path names it the same way, over whatever
# reason (the wrapped authority's own words, relayed by enact above this line, or a
# usage error with no command to relay). ENVELOPE_SAID is a plain global, not a
# merge()-local: the EXIT trap below that makes the envelope STRUCTURAL cannot see a
# function's locals (traps run outside the call stack that set them), only globals.
ENVELOPE_SAID=""
refuse() {
  echo "NOT merged: $1" >&2
  ENVELOPE_SAID=1
  exit 1
}

merge() {
  local pr="${1-}" dry=""
  ENVELOPE_SAID=""
  # The structural guarantee (#266): whatever ends this function — a refuse() above,
  # an uncaught failure this sweep missed, a future edit that adds one — the envelope
  # speaks. Cleared at every clean exit (the dry-run return, the merged: line); left
  # armed, it is the last word instead of silence.
  trap '[[ -n "$ENVELOPE_SAID" ]] || echo "NOT merged: merge() ended without a stated verdict — see the output above" >&2' EXIT
  [[ "${2-}" == "--dry-run" ]] && dry=1
  [[ "$pr" == "--dry-run" ]] && refuse "--dry-run comes after the PR"
  [[ -n "$pr" ]] || refuse "which PR? (a number, a URL, or a branch)"

  # The one operation here that writes to a server other people see, and its whole audit
  # trail was terminal scrollback. Path per the command/verb rule (#54).
  local log
  log="$REPO_DIR/tmp/logs/forge/merge/$(date -u '+%Y-%m-%dT%H:%M:%SZ').log"
  mkdir -p "$(dirname "$log")"
  exec > >(tee -a "$log") 2>&1
  echo "yoga forge merge $pr — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

  # 0. the sends ARE the work here (gh pr view, gh pr merge): refuse loudly, first (#29)
  assert_may_send "gh pr view / gh pr merge (yoga forge merge)" || refuse "sends refused (see above)"

  # 1. the forge itself: merging under undeclared settings composes main by rules nobody wrote
  status || refuse "REFUSE-class ✗ above (settings drift or a wrong hook): the squash would land badly; each line names its remedy"
  [[ "$STATUS_TIDY" -eq 0 ]] || echo "note: tidy-class ✗ above (stale refs / deletable branches) — bookkeeping, not danger; this merge's own tidy-up clears what it can, and yoga forge prune covers the rest"

  # 2. the PR's own state, from the forge rather than from optimism
  local json
  json="$(cd "$REPO_DIR" && quiet gh pr view "$pr" \
    --json number,title,state,isDraft,mergeable,mergeStateStatus,headRefName,headRefOid,commits,body,baseRefOid)" \
    || refuse "no such PR: $pr"
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
    [[ "$state"     == OPEN      ]] || refuse "#$n is $state — nothing to merge"
    [[ "$draft"     == false     ]] || refuse "#$n is a draft — mark it ready first"
    [[ "$mergeable" != UNKNOWN    ]] || refuse "#$n is UNKNOWN — the forge is recomputing mergeability (usual after a push); retry in a moment"
    [[ "$mergeable" == MERGEABLE ]] || refuse "#$n is $mergeable ($mstate) — resolve that first; gh would fail or prompt"
  fi
  # BEHIND matters for more than tidiness: a squash of an up-to-date branch lands exactly
  # the branch's tree, which its own pre-commit hook already gated. Behind main, the merged
  # tree is a combination nothing has ever checked.
  [[ -n "$already" || "$mstate" == CLEAN ]] || refuse "#$n is $mstate — a squash of a branch that is not up to date lands a tree no gate has seen; rebase it onto main first"

  # 2b. the postcondition moves HEAD to the base branch, so the tree must be clean FIRST:
  # a merge that lands and then cannot tidy up is worse than one that refuses early.
  local base current
  base="$(base_branch)"
  current="$(quiet git -C "$REPO_DIR" branch --show-current)"

  # 3. the INTENT: exactly what will land, since afterwards the parts are unreachable
  echo
  echo "the message the forge will assemble (squash_merge_commit_message: COMMIT_MESSAGES):"
  echo "  $title (#$n)"
  jq -r '.commits[] | "  * " + (.messageHeadline)' <<< "$json"
  local sigs
  sigs=$(jq -r '[.commits[] | select(.messageBody | test("(^|\n)Signature:"))] | length' <<< "$json")
  echo "  — $(jq -r '.commits | length' <<< "$json") commit(s), $sigs carrying a Signature"
  [[ "$sigs" -gt 0 ]] || echo "  ⚠ no commit carries a Signature: main would gain history no session can be joined to"
  # the surface roster (#136) needs the head objects locally; the fetch is the same
  # wire read step 5 performs after the merge, moved earlier
  enact git -C "$REPO_DIR" fetch --quiet origin "$head" || true
  local roster base_at
  roster="$(surface_roster "origin/$base" "$oid")"
  base_at="$(quiet git -C "$REPO_DIR" rev-parse --short "origin/$base" || echo '?')"
  if [[ -n "$roster" ]]; then
    echo "  the command surface, after this merge (diffed against origin/$base@$base_at; judgment stays the PR's what):"
    printf '%s\n' "$roster"
  fi
  jq -r '.body // ""' <<< "$json" | totest_check
  # THE mood check (#153, superseding the phrase-sniffing the maintainer condemned):
  # the forge already wrote the one closing parser that will act, so consult IT and
  # nothing else. Under the law that every PR closes an issue, "their parser sees no
  # close" means the branch is still prospective (or mis-armed) — either way, not
  # mergeable. No phrases, no dialects, no mention-stripping: prose is free; the
  # field decides. (#146: shown before consent; #29/#127: the strikes it catches.)
  local will_close
  will_close="$(cd "$REPO_DIR" && quiet gh pr view "$n" --json closingIssuesReferences \
    --jq '[.closingIssuesReferences[].number] | map("#\(.)") | join(", ")' || true)"
  echo "  the forge will close: ${will_close:-nothing}"
  [[ -n "$will_close" || -n "$already" ]] || echo "  ⚠ nothing closes — every PR closes an issue; a real run refuses until closes #N is armed and pushed"

  echo
  # A PREDICTION, so it speaks the prospective — and its MODAL follows the MODE:
  # the dry run says "would" (its antecedent is the consent being withheld — the
  # prune precedent: "would delete … pass --apply"); the real run says "will" (the
  # command was typed; nothing conditional remains but the checks). And it EVALUATES
  # its conditionals: the containment test is decidable now, and a printed "if"
  # whose inputs are in hand is a hedge dressed as a fact (the specimens on #146:
  # perfect-tense lines narrating a merge the next line refused; then a "would"
  # offered for the real run, corrected by the maintainer with one word).
  local modal="will"; [[ -z "$dry" ]] || modal="would"
  echo "the state this $modal leave behind:"
  [[ -n "$already" ]] && echo "  #$n — already merged into $base (the forge half is done)" \
                      || echo "  #$n — merges into $base"
  if [[ "$current" == "$head" ]]; then
    echo "  this checkout — moves from $head to $base"
  elif [[ -n "$current" ]]; then
    echo "  this checkout — stays on $current"
  else
    # a detached HEAD has no name to stay on — say where it stands instead of
    # rendering a blank where a name belongs (the review's first misstatement)
    echo "  this checkout — stays detached at $(quiet git -C "$REPO_DIR" rev-parse --short HEAD || echo '?')"
  fi
  echo "  $base — fast-forwards to include it"
  local head_tip=""
  # --verify --quiet, or rev-parse ECHOES an unresolvable name to stdout — which
  # filled head_tip with a literal refs/heads/ string and made the KEPT line assert
  # a specific reason about a branch that does not exist (the review's second).
  # A predicate over local refs, not an enactment: "no such ref" here is a normal
  # answer, not a failure to relay.
  head_tip="$(git -C "$REPO_DIR" rev-parse --verify --quiet "refs/heads/$head" || true)"
  if [[ -z "$head_tip" ]]; then
    echo "  $head — is not here (nothing to delete)"
  elif [[ "$head_tip" == "$oid" ]] || git -C "$REPO_DIR" merge-base --is-ancestor "$head_tip" "$oid" 2>/dev/null; then
    echo "  $head — $modal be deleted here (its tip is contained in the merged head)"
  else
    echo "  $head — $modal be KEPT here (it holds commits the head being merged does not)"
  fi
  [[ -z "$dry" ]] || { echo; echo "--dry-run: nothing merged"; ENVELOPE_SAID=1; trap - EXIT; return 0; }

  [[ -n "$will_close" || -n "$already" ]] || refuse "the forge's own parser will close nothing, and every PR closes an issue: arm closes #N (or link the issue on the forge) and push before merging"

  # 4. the effect. No --subject, no --body: the forge assembles the message from the
  # commits, which is where the signatures are. --match-head-commit closes the race
  # between the head just inspected and the head merged. Wrapped and echoed (#274):
  # the refusal, if any, is git's or gh's own — relayed above, never re-diagnosed here.
  echo
  # off the branch BEFORE merging: a branch checked out here cannot be deleted, and the
  # tidy-up is part of what `merge` promises, not a courtesy attempted afterwards
  if [[ "$current" == "$head" ]]; then
    enact git -C "$REPO_DIR" checkout --quiet "$base" || refuse "could not switch to $base"
  fi
  if [[ -z "$already" ]]; then
    (cd "$REPO_DIR" && enact gh pr merge "$n" --squash --match-head-commit "$oid") \
      || refuse "gh pr merge refused (see above)"
  fi

  # 5. the extent afterwards. delete_branch_on_merge removes the REMOTE branch; the local
  # one survives, and a squash makes it look unmerged to git — so `git branch -d` refuses
  # and only -D will do it. The safety therefore cannot come from git's opinion: it comes
  # from comparing the local tip with the head we just merged. Equal means everything local
  # is in the squash; different means unpushed work, and the branch stays.
  echo
  # fetch WITHOUT pruning: the fast-forward below needs origin/$base, but pruning here
  # asks the server before it has finished deleting the head branch (see the end).
  enact git -C "$REPO_DIR" fetch --quiet origin || true
  # the base must actually HOLD the squash here, or the next thing anyone types is a manual
  # pull — the same residue in another shape. A skipped courtesy, not a refusal (#273 into
  # #274): a real run has already landed the squash by this point.
  if enact git -C "$REPO_DIR" merge --ff-only --quiet "origin/$base"; then
    echo "local: $base fast-forwarded to $(quiet git -C "$REPO_DIR" rev-parse --short HEAD || echo '?')"
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
      enact git -C "$REPO_DIR" branch -D "$head" >/dev/null && echo "local: $head deleted — $detail"
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
  # show-ref is a predicate over local refs, not an enactment — left unwrapped, as
  # merge-base --is-ancestor is above; only remote prune, the mutation, is wrapped.
  local tracked=""
  git -C "$REPO_DIR" show-ref --verify --quiet "refs/remotes/origin/$head" && tracked=1
  enact git -C "$REPO_DIR" remote prune origin || true
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

  # 7. issues, after this merge — verified from the forge, never assumed (#146).
  # Declared closes come from the parser's OWN declaration — closingIssuesReferences,
  # already fetched pre-merge as will_close — never from the squash message: the mood
  # law (#154) keeps every commit subject lawfully closes-free, so a squash-message
  # grep for "closes #N" finds nothing on a lawful merge, every time (#278). Declared-
  # and-CLOSED is the contract kept; declared-but-open is the failed close; CLOSED-
  # but-undeclared is the parser strike (the #29/#127/#259 class) — a lawful merge
  # alarms on neither. Checked is the union of what the squash message names (#N,
  # mentions stripped of backticked spans) and what the parser declared: COMMIT_MESSAGES
  # draws the squash text from commit subjects, not the PR body, so a declared close can
  # be entirely absent from that text and still needs its checkmark. Every grep here can
  # lawfully match nothing — piped to `|| true`, since no-match is an answer, not a
  # failure (#278).
  # The strike verdict requires causation (#284): an issue counts as closed BY THIS
  # MERGE only when its own timeline close event is stamped with this merge's squash
  # sha — the exact forensic that convicted the real strike, #259, closed via a stale
  # commit-subject whose close event carries #258's own squash sha. A close stamped
  # with no commit, or another commit, is another actor's lawful act: reported at
  # most as a reference, never accused of this merge's silence. Step 5's fetch
  # already updated origin/$base locally; its tip IS the squash this merge landed,
  # read here rather than asked of the forge a second time.
  local squash_msg declared_closes mentioned iss st_i squash_sha
  squash_sha="$(quiet git -C "$REPO_DIR" rev-parse "origin/$base" || true)"
  squash_msg="$(quiet git -C "$REPO_DIR" show -s --format=%B "origin/$base" || true)"
  declared_closes="$(grep -oE '[0-9]+' <<< "$will_close" || true)"
  # shellcheck disable=SC2016  # backticks are sed pattern, not expansion
  mentioned="$(printf '%s' "$squash_msg" | sed 's/`[^`]*`//g' | grep -oE '#[0-9]+' | grep -oE '[0-9]+' || true)"
  mentioned="$(sort -u <<< "$mentioned"$'\n'"$declared_closes" | sed '/^$/d')"
  if [[ -n "$mentioned" ]]; then
    echo
    echo "issues, after this merge (verified from the forge):"
    while read -r iss; do
      [[ -n "$iss" ]] || continue
      st_i="$(cd "$REPO_DIR" && quiet gh issue view "$iss" --json state --jq .state || echo UNKNOWN)"
      if grep -qx "$iss" <<< "$declared_closes"; then
        [[ "$st_i" == CLOSED ]] && echo "  ✓ #$iss — declared closes, and CLOSED" \
                                || echo "  ⚠ #$iss — declared closes, but $st_i: the close did not fire"
      elif [[ "$st_i" == CLOSED ]]; then
        # Who closed it: the timeline's own closed event names the commit, if any
        # (--paginate follows a timeline longer than one page). No commit, or a
        # different one, is a lawful act by another merge or the PR body directly.
        local closed_by
        closed_by="$(cd "$REPO_DIR" && quiet gh api "repos/{owner}/{repo}/issues/$iss/timeline" \
          --paginate --jq '[.[] | select(.event == "closed")] | last | .commit_id // empty' || true)"
        if [[ -n "$squash_sha" && "$closed_by" == "$squash_sha" ]]; then
          echo "  ⚠⚠ #$iss — CLOSED but NOT declared: a parser strike; reopen if unintended"
        else
          echo "  – #$iss — mentioned, CLOSED elsewhere — a reference"
        fi
      else
        echo "  – #$iss — mentioned, $st_i (no close declared: a reference)"
      fi
    done <<< "$mentioned"
  fi

  # 8. the enactment envelope (#266): the last line states what landed, sourced from
  # the forge's own answer — never inferred from the tidy-up above.
  echo
  local landed
  landed="$(cd "$REPO_DIR" && quiet gh pr view "$n" --json mergeCommit --jq '.mergeCommit.oid // empty')"
  if [[ -n "$landed" ]]; then
    echo "merged: #$n as ${landed:0:8} on $base"
    ENVELOPE_SAID=1
    trap - EXIT
  else
    refuse "gh reports no merge commit for #$n (see above)"
  fi
}

# Sourced, this file is its derivations and nothing else: a caller that wants one row set
# gets that one, at the cost of deriving it. Run, it dispatches. Without this line the two
# uses were the same use — reaching `reconcile` meant running the program, so the machine
# report paid for a `gh pr list --state all --limit 200` and a `git remote prune --dry-run`
# whose rows it then discarded unread: 2.5s of which 2.4s was network it did not want.
[[ "${BASH_SOURCE[0]}" == "${0}" ]] || return 0

case "${1-}" in
  '')        status ;;
  sync)      shift; sync "$@" ;;
  prune)     shift; prune "$@" ;;
  merge)     shift; merge "$@" ;;
  --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0" ;;
  *)         echo "yoga forge: unknown argument: $1 (try: yoga forge --help)" >&2; exit 1 ;;
esac
