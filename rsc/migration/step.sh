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
MOVED=()
case "${1-}" in
  --apply) APPLY=1 ;;
  '') ;;
  *) echo "usage: $SELF [--apply]" >&2; exit 2 ;;
esac

# move <from> <to>: a file or directory at a former address to its current one.
move() {
  local from="$1" to="$2"
  [[ -e "$from" || -L "$from" ]] || return 0
  if [[ -e "$to" || -L "$to" ]]; then
    echo "FAIL: $from and $to both exist - resolve by hand, then run $SELF again" >&2
    exit 1
  fi
  echo "mv $from $to"
  if (( APPLY )); then mkdir -p "$(dirname "$to")" && mv "$from" "$to"; else MOVED+=("$from"); fi
}

# remove <link>: a symlink at a retired address; a file or directory there is not a
# link and is not touched.
remove() {
  local link="$1"
  [[ -L "$link" ]] || return 0
  echo "rm $link"
  if (( APPLY )); then rm "$link"; fi
}

# retire <directory>: a directory nothing writes any more, removed once empty - bare,
# once the moves stated above it would have emptied it; a directory still holding
# files is named and left.
retire() {
  local dir="$1" entry moved
  [[ -d "$dir" && ! -L "$dir" ]] || return 0
  for entry in "$dir"/* "$dir"/.[!.]*; do
    [[ -e "$entry" || -L "$entry" ]] || continue
    for moved in ${MOVED[@]+"${MOVED[@]}"}; do [[ "$entry" == "$moved" ]] && continue 2; done
    echo "FAIL: $dir still holds $entry - move or remove it by hand, then run $SELF again" >&2
    exit 1
  done
  echo "rmdir $dir"
  if (( APPLY )); then rmdir "$dir"; fi
}
