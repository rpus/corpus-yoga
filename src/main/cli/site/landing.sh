# shellcheck shell=bash
# landing.sh - what corpus-yoga site publish would land on rpus.co, read against rpus.co as it
# stands (issues/1020): the publish tree against the clone's origin as last fetched, never
# against the clone's files as they last stood. Sourced by src/main/cli/site/site.sh after
# report.sh, send.sh and enact.sh; each function takes the clone, and the tree where it reads one.

# clone_origin <clone>: the branch of rpus.co the clone tracks, as git names it; HEAD where it
# tracks none.
clone_origin() {
  git -C "$1" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || echo HEAD
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
# stands to its origin; diverged carries the command that shows where they part.
clone_position() {
  local origin ahead behind
  origin="$(clone_origin "$1")"
  if [[ "$origin" == HEAD ]]; then
    printf 'clone\t%s\n' "$(phrase "tracks no branch of rpus.co - read against its own HEAD")"
    return 0
  fi
  read -r ahead behind < <(git -C "$1" rev-list --left-right --count "HEAD...$origin")
  if (( ahead == 0 && behind == 0 )); then
    printf 'clone\t%s\n' "$(phrase "level with {origin}" origin="$origin")"
  elif (( ahead == 0 )); then
    printf 'clone\t%s\n' "$(phrase "behind {origin} by {n} commit(s) - the next corpus-yoga site publish brings it level" origin="$origin" n="$behind")"
  elif (( behind == 0 )); then
    printf 'clone\t%s\n' "$(phrase "ahead of {origin} by {n} commit(s) - the next corpus-yoga site publish pushes them" origin="$origin" n="$ahead")"
  else
    printf 'clone\t%s\t%s\t%s\n' \
      "$(phrase "diverged from {origin} - {ahead} commit(s) here, {behind} there; corpus-yoga site publish refuses until they are reconciled" origin="$origin" ahead="$ahead" behind="$behind")" \
      "git -C ext/mnt/site status" "$(phrase "shows where the clone and rpus.co part")"
  fi
}

# landing <clone> <tree>: the rows `land <file> <what changes>` - each new or changed file of the
# tree against the clone's origin (deletions are not mirrored - the site repo curates its own
# removals), the corpus page in the page's own terms (src/main/model/compare_pages.py, issues/652),
# since a line diff of two renders misstates it; and the clone's own uncommitted files, which
# the copy commits with it.
landing() {
  local clone="$1" tree="$2" origin held f rel
  [[ -d "$clone/.git" && -d "$tree" ]] || return 0
  origin="$(clone_origin "$clone")"
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

# level_clone <clone>: the clone brought level with its origin by a fast-forward, the act's first
# step; non-zero where it cannot be - diverged, or the send refused.
level_clone() {
  assert_may_send "git -C ext/mnt/site pull --ff-only (site publish)" || return 1
  [[ "$(clone_origin "$1")" == HEAD ]] && return 0
  enact git -C "$1" pull --ff-only --quiet
}
