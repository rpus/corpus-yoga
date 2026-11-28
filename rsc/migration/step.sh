# shellcheck shell=bash
# rsc/migration/step.sh - the steps a migration script is made of, sourced by each
# rsc/migration/<issue>.sh. A step is guarded so that a second
# run does nothing; bare, the script states each step it would take, and --apply takes
# them. A from and a to both present halt with the pair named: nothing here chooses.

REPO_DIR="${CORPUS_YOGA_ROOT:?the repository root, which corpus-yoga hands every run it starts}"
MIGRATION="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)/$(basename "${BASH_SOURCE[1]}")"
MIGRATION="${MIGRATION#"$REPO_DIR"/}"   # the running migration, as its messages name it
cd "$REPO_DIR" || exit 1

APPLY=0
MOVED=()     # bare: what the moves stated above would have taken away
ARRIVED=()   # bare: where the moves stated above would have put something
case "${1-}" in
  --apply) APPLY=1 ;;
  '') ;;
  *) echo "usage: $MIGRATION [--apply]" >&2; exit 2 ;;
esac

# stands <path>: whether something stands at the path once the steps stated above are taken -
# bare, what they would have moved away or put there counted as done.
stands() {
  local path="$1" entry
  for entry in ${ARRIVED[@]+"${ARRIVED[@]}"}; do [[ "$path" == "$entry" ]] && return 0; done
  for entry in ${MOVED[@]+"${MOVED[@]}"}; do [[ "$path" == "$entry" ]] && return 1; done
  [[ -e "$path" || -L "$path" ]]
}

# move <from> <to>: a file or directory at a former address to its current one.
move() {
  local from="$1" to="$2"
  stands "$from" || return 0
  if stands "$to"; then
    echo "FAIL: $from and $to both exist - resolve by hand, then run $MIGRATION again" >&2
    exit 1
  fi
  echo "mv $from $to"
  if (( APPLY )); then mkdir -p "$(dirname "$to")" && mv "$from" "$to"; else MOVED+=("$from"); ARRIVED+=("$to"); fi
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
# removed with what it holds, its read-only directories made writable first; only under tmp/cache,
# where every file is a derivation some verb rewrites, a __pycache__ under src, the bytecode python
# rebuilds under tmp/cache/python (issues/1052), stage/dev, which every dev gate run made afresh
# (issues/1171), or the working files of a finished rehearsal, stage/scratch/tmp and
# stage/scratch/extent.json (issues/1163).
discard() {
  local entry="$1"
  [[ "$entry" == tmp/cache/* || "$entry" == src/__pycache__ || "$entry" == src/*/__pycache__ || "$entry" == stage/dev \
     || "$entry" == stage/scratch/tmp || "$entry" == stage/scratch/extent.json ]] \
    || { echo "FAIL: discard $entry - only an entry under tmp/cache, a __pycache__ under src, stage/dev or a finished rehearsal's working files is discarded" >&2; exit 1; }
  [[ -e "$entry" && ! -L "$entry" ]] || return 0
  echo "rm -r $entry"
  if (( APPLY )); then chmod -R u+w "$entry" && rm -r "$entry"; else MOVED+=("$entry"); fi
}

# sever <link>: a symbolic link a retired layout made, removed; what it points at stands.
sever() {
  local link="$1"
  [[ -L "$link" ]] || return 0
  echo "rm $link"
  if (( APPLY )); then rm "$link"; else MOVED+=("$link"); fi
}

# dispose <entry>: an agent's memory directory the store or the stage holds,
# <root>/claude/code/machine-transport/<room>/<project>/memory, removed whole, its files
# counted and sized on the line before it goes (issues/1090); or a record of the indexing
# judgement, its lines and bytes counted (issues/1189) - the disposal record, which the
# migration's log keeps.
dispose() {
  local dir="$1" files bytes
  if [[ "$dir" =~ ^data/output/indexing/(accepted|rejected)-semantic-concepts\.txt$ || "$dir" == cache/indexing/candidate-semantic-concepts.txt ]]; then
    # the indexing judgement's records, retired with it (issues/1189): a file, counted by its lines
    [[ -f "$dir" && ! -L "$dir" ]] || return 0
    echo "rm $dir - $(wc -l < "$dir" | tr -d ' ') line(s), $(wc -c < "$dir" | tr -d ' ') bytes"
    if (( APPLY )); then rm "$dir"; else MOVED+=("$dir"); fi
    return 0
  fi
  [[ "$dir" =~ ^(data/input|tmp/stage/input)/claude/code/machine-transport/[^/]+/[^/]+/memory$ ]] \
    || { echo "FAIL: dispose $dir - only an agent's memory directory under data/input or tmp/stage/input, or the indexing judgement's records, is disposed of" >&2; exit 1; }
  [[ -d "$dir" && ! -L "$dir" ]] || return 0
  files="$(find "$dir" -type f ! -name .DS_Store | wc -l | tr -d ' ')"
  bytes="$(find "$dir" -type f ! -name .DS_Store -exec cat {} + | wc -c | tr -d ' ')"
  echo "rm -r $dir - $files file(s), $bytes bytes"
  if (( APPLY )); then rm -r "$dir"; else MOVED+=("$dir"); fi
}

# fold <from> <to>: every file and link under a directory at a former address, moved to the same
# place under its current one, which may already stand - the new code writes there before the room
# migrates. A file standing at both halts with the pair named, before anything moves; the emptied
# directories at the former address are removed.
fold() {
  local from="$1" to="$2" file rel gone n=0
  [[ -d "$from" && ! -L "$from" ]] || return 0
  while IFS= read -r -d '' file; do
    for gone in ${MOVED[@]+"${MOVED[@]}"}; do [[ "$file" == "$gone"/* ]] && continue 2; done
    rel="${file#"$from"/}"
    if [[ -e "$to/$rel" || -L "$to/$rel" ]]; then
      echo "FAIL: $file and $to/$rel both exist - resolve by hand, then run $MIGRATION again" >&2
      exit 1
    fi
    n=$((n + 1))
  done < <(find "$from" \( -type f -o -type l \) -print0)
  echo "fold $from into $to - $n file(s)"
  if (( APPLY )); then
    while IFS= read -r -d '' file; do
      rel="${file#"$from"/}"
      mkdir -p "$(dirname "$to/$rel")" && mv "$file" "$to/$rel"
    done < <(find "$from" \( -type f -o -type l \) -print0)
    find "$from" -depth -type d -empty -delete
  else
    MOVED+=("$from"); ARRIVED+=("$to")
  fi
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
    echo "FAIL: $dir still holds $entry - move or remove it by hand, then run $MIGRATION again" >&2
    exit 1
  done
  echo "rmdir $dir"
  if (( APPLY )); then rm -f "$dir/.DS_Store" && rmdir "$dir"; else MOVED+=("$dir"); fi
}
