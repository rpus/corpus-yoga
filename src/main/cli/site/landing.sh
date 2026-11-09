# shellcheck shell=bash
# landing.sh - what corpus-yoga site publish would land on rpus.co, read against rpus.co as it
# stands (issues/1020): the publish tree against the clone's origin as last fetched, never
# against the clone's files as they last stood. Sourced by src/main/cli/site/site.sh after
# report.sh, send.sh and enact.sh; each function takes the clone, and the tree where it reads one.

# clone_served <clone>: the branch rpus.co serves, the remote's default as the clone records it
# (origin/HEAD), whatever branch the clone has checked out (issues/1026); nothing where it records none.
clone_served() {
  git -C "$1" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || true
}

# off_served <clone>: the branch the clone stands on, where it is not the one rpus.co serves;
# nothing where it is, or where no served branch is recorded.
off_served() {
  local served branch
  served="$(clone_served "$1")"
  branch="$(git -C "$1" branch --show-current)"
  [[ -n "$served" && "$branch" != "${served#*/}" ]] && echo "${branch:-a detached HEAD}"
  return 0
}

# clone_fetch <clone>: the clone's record of rpus.co brought level within the send bound; a row
# `fetch <words>` where it could not be, so that what is read after it is said as last fetched.
clone_fetch() {
  if ! may_send; then
    printf 'fetch\t%s\n' "$(phrase "unverified - CORPUS_YOGA_NO_SEND=1 refuses the fetch; read against rpus.co as last fetched")"
  elif ! quiet git -C "$1" fetch --quiet; then
    printf 'fetch\t%s\n' "$(phrase "unverified - the fetch of rpus.co did not answer; read against rpus.co as last fetched")"
  fi
  return 0
}

# clone_position <clone>: the row `clone <words> [<command> <what it does>]` - where the clone
# stands to the branch rpus.co serves; a clone that records no served branch, stands on another
# branch, or has diverged carries the command that answers it, and publish refuses it.
clone_position() {
  local served off ahead behind
  served="$(clone_served "$1")"
  if [[ -z "$served" ]]; then
    printf 'clone\t%s\t%s\t%s\n' "$(phrase "records no branch rpus.co serves (origin/HEAD) - corpus-yoga site publish refuses until it does")" \
      "git -C ext/mnt/site remote set-head origin --auto" "$(phrase "records the remote's default branch")"
    return 0
  fi
  off="$(off_served "$1")"
  if [[ -n "$off" ]]; then
    printf 'clone\t%s\t%s\t%s\n' "$(phrase "on {branch}, not {local}, the branch rpus.co serves as {served} - corpus-yoga site publish refuses until it stands on {local}" branch="$off" local="${served#*/}" served="$served")" \
      "git -C ext/mnt/site switch ${served#*/}" "$(phrase "stands it on the branch rpus.co serves")"
    return 0
  fi
  read -r ahead behind < <(git -C "$1" rev-list --left-right --count "HEAD...$served")
  if (( ahead == 0 && behind == 0 )); then
    printf 'clone\t%s\n' "$(phrase "level with {origin}" origin="$served")"
  elif (( ahead == 0 )); then
    printf 'clone\t%s\n' "$(phrase "behind {origin} by {n} commit(s) - the next corpus-yoga site publish brings it level" origin="$served" n="$behind")"
  elif (( behind == 0 )); then
    printf 'clone\t%s\n' "$(phrase "ahead of {origin} by {n} commit(s) - the next corpus-yoga site publish pushes them" origin="$served" n="$ahead")"
  else
    printf 'clone\t%s\t%s\t%s\n' \
      "$(phrase "diverged from {origin} - {ahead} commit(s) here, {behind} there; corpus-yoga site publish refuses until they are reconciled" origin="$served" ahead="$ahead" behind="$behind")" \
      "git -C ext/mnt/site status" "$(phrase "shows where the clone and rpus.co part")"
  fi
}

# landing <clone> <tree>: the rows `land <file> <what changes>` - each new or changed file of the
# tree against the branch rpus.co serves (deletions are not mirrored - the site repo curates its own
# removals), the corpus page in the page's own terms (src/main/model/compare_pages.py, issues/652),
# since a line diff of two renders misstates it; and the clone's own uncommitted files, which
# the copy commits with it.
landing() {
  local clone="$1" tree="$2" origin held f rel
  [[ -d "$clone/.git" && -d "$tree" ]] || return 0
  origin="$(clone_served "$clone")"
  [[ -n "$origin" ]] || origin=HEAD
  held="$(mktemp "${TMPDIR:-/tmp}/landing.XXXXXX")"
  while IFS= read -r f; do
    rel="${f#"$tree"/}"
    if ! git -C "$clone" show "$origin:$rel" > "$held" 2>/dev/null; then
      printf 'land\t%s\t%s\n' "$rel" "$(phrase "new on rpus.co")"
    elif ! cmp -s "$f" "$held"; then
      if [[ "$rel" == index.html ]]; then
        # one row per line of the comparison: each a fact of the page, which the status
        # nests beneath the file, never one sentence; a comparison that fails is said as a
        # change the comparison could not word, never read as nothing to land (issues/1000)
        local compared line
        if compared="$("$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/model/compare_pages.py" "$held" "$f")"; then
          # only what changes is said (issues/1028); a page whose bytes differ outside every table it
          # declares still changes, and says so
          [[ -n "$compared" ]] || compared="$(phrase "changed - outside every table the page declares")"
          while IFS= read -r line; do
            [[ -n "$line" ]] && printf 'land\t%s\t%s\n' "$rel" "$line"
          done <<< "$compared"
        else
          printf 'land\t%s\t%s\n' "$rel" "$(phrase "changed - the comparison failed; its output above says where")"
        fi
      else
        printf 'land\t%s\t%s\n' "$rel" "$(phrase "changed")"
      fi
    fi
  done < <(find "$tree" -type f | sort)
  rm -f "$held"
  [[ -n "$(git -C "$clone" status --porcelain)" ]] && printf 'land\t%s\t%s\n' "(the clone's own uncommitted changes)" "$(phrase "committed with the copy")"
  return 0
}

# level_clone <clone>: the clone brought level with the branch rpus.co serves by a fast-forward,
# the act's first step; non-zero where it cannot be - no served branch recorded, the clone on
# another branch, diverged, or the send refused.
level_clone() {
  local served
  assert_may_send "git -C ext/mnt/site pull --ff-only (site publish)" || return 1
  served="$(clone_served "$1")"
  [[ -n "$served" && -z "$(off_served "$1")" ]] || return 1
  enact git -C "$1" pull --ff-only --quiet origin "${served#*/}"
}
