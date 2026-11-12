# shellcheck shell=bash
# rsc/migration/step.sh - the steps a migration script is made of, sourced by each
# rsc/migration/<issue>.sh after it declares SELF. A step is guarded so that a second
# run does nothing; bare, the script states each step it would take, and --apply takes
# them. A from and a to both present halt with the pair named: nothing here chooses.

[[ -n "${SELF-}" ]] || { echo "${BASH_SOURCE[1]}: declares no SELF" >&2; exit 1; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[1]}" ]] || { echo "${BASH_SOURCE[1]}: not at its declared address $SELF" >&2; exit 1; }
cd "$REPO_DIR" || exit 1

APPLY=0
MOVED=()     # bare: what the moves stated above would have taken away
REMOVED=()   # bare: the links the removes stated above would have taken away
ARRIVED=()   # bare: where the moves stated above would have put something
case "${1-}" in
  --apply) APPLY=1 ;;
  '') ;;
  *) echo "usage: $SELF [--apply]" >&2; exit 2 ;;
esac

# stands <path>: whether something stands at the path once the steps stated above are taken -
# bare, what they would have removed, moved away or put there counted as done.
stands() {
  local path="$1" entry
  for entry in ${ARRIVED[@]+"${ARRIVED[@]}"}; do [[ "$path" == "$entry" ]] && return 0; done
  for entry in ${REMOVED[@]+"${REMOVED[@]}"} ${MOVED[@]+"${MOVED[@]}"}; do [[ "$path" == "$entry" ]] && return 1; done
  [[ -e "$path" || -L "$path" ]]
}

# move <from> <to>: a file or directory at a former address to its current one.
move() {
  local from="$1" to="$2"
  stands "$from" || return 0
  if stands "$to"; then
    echo "FAIL: $from and $to both exist - resolve by hand, then run $SELF again" >&2
    exit 1
  fi
  echo "mv $from $to"
  if (( APPLY )); then mkdir -p "$(dirname "$to")" && mv "$from" "$to"; else MOVED+=("$from"); ARRIVED+=("$to"); fi
}

# remove <link>: a symlink at a retired address; a file or directory there is not a
# link and is not touched.
remove() {
  local link="$1"
  [[ -L "$link" ]] || return 0
  echo "rm $link"
  if (( APPLY )); then rm "$link"; else REMOVED+=("$link"); fi
}

# release <entry> <record>: a live file or directory the store holds byte for byte at record,
# removed - the store's copy is the record, so nothing is lost; an entry the store does not
# hold so is left for the steps after it.
release() {
  local entry="$1" record="$2"
  stands "$entry" && [[ ! -L "$entry" ]] || return 0
  diff -rq "$entry" "$record" >/dev/null 2>&1 || return 0
  echo "rm -r $entry - $record holds it"
  if (( APPLY )); then rm -r "$entry"; else MOVED+=("$entry"); fi
}

# strip <file> <prefix>: the lines of a file that begin with the prefix, removed; every
# other line kept as it stands.
strip() {
  local file="$1" prefix="$2" n
  [[ -f "$file" ]] || return 0
  n="$(awk -v p="$prefix" 'index($0, p) == 1 { n++ } END { print n + 0 }' "$file")"
  (( n > 0 )) || return 0
  echo "strip $n line(s) beginning $prefix from $file"
  if (( APPLY )); then awk -v p="$prefix" 'index($0, p) != 1' "$file" > "$file.stripped" && mv "$file.stripped" "$file"; fi
}

# discard <entry>: a file or directory of rebuildable derivations at a retired address,
# removed with what it holds; only under tmp/cache, where every file is a derivation some
# verb rewrites, or what the rehearsal layout before issues/815 left under tmp/stage - a stamped
# rehearsal under tmp/stage/rehearsal/, or the record under that name before its extension
# - which corpus-yoga pipeline rehearse remakes under tmp/stage/scratch and tmp/stage/rehearsal.json,
# or a __pycache__ under src, the bytecode python rebuilds under tmp/cache/python (issues/1052).
discard() {
  local entry="$1"
  [[ "$entry" == tmp/cache/* || "$entry" == tmp/stage/rehearsal || "$entry" == tmp/stage/rehearsal/* || "$entry" == src/__pycache__ || "$entry" == src/*/__pycache__ ]] \
    || { echo "FAIL: discard $entry - only an entry under tmp/cache or tmp/stage/rehearsal, or a __pycache__ under src, is discarded" >&2; exit 1; }
  [[ -e "$entry" && ! -L "$entry" ]] || return 0
  echo "rm -r $entry"
  if (( APPLY )); then rm -r "$entry"; else MOVED+=("$entry"); fi
}

# retire <directory>: a directory nothing writes any more, removed once empty - bare,
# once the moves stated above it would have emptied it; a directory still holding
# files is named and left. Finder's .DS_Store is no file of it: Finder writes one into
# any directory it shows, and rebuilds it.
retire() {
  local dir="$1" entry moved
  [[ -d "$dir" && ! -L "$dir" ]] || return 0
  for entry in "$dir"/* "$dir"/.[!.]*; do
    [[ -e "$entry" || -L "$entry" ]] || continue
    [[ "${entry##*/}" == .DS_Store ]] && continue
    for moved in ${MOVED[@]+"${MOVED[@]}"}; do [[ "$entry" == "$moved" ]] && continue 2; done
    echo "FAIL: $dir still holds $entry - move or remove it by hand, then run $SELF again" >&2
    exit 1
  done
  echo "rmdir $dir"
  if (( APPLY )); then rm -f "$dir/.DS_Store" && rmdir "$dir"; else MOVED+=("$dir"); fi
}
