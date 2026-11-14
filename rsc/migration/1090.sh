#!/usr/bin/env bash
# rsc/migration/1090.sh - the corpus holds no agent memory (issues/1090): each memory directory
# the store or the stage holds under claude's machine transport is disposed of, once a stored
# or staged session's tool calls wrote each of its files by name - a twin a pull wrote,
# <stem>.<room>.md, by the name of the fact it twins, <stem>.md. A file no session wrote halts
# the script before anything goes, named: no log holds its text, and whether it goes is the
# maintainer's ruling.
set -euo pipefail
SELF='rsc/migration/1090.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

roots=()
for root in data/input/claude/code/machine-transport tmp/stage/input/claude/code/machine-transport; do
  [[ -d "$root" ]] && roots+=("$root")
done
(( ${#roots[@]} )) || exit 0
dirs=()
while IFS= read -r dir; do
  dirs+=("$dir")
done < <(find "${roots[@]}" -mindepth 3 -maxdepth 3 -type d -name memory | sort)
(( ${#dirs[@]} )) || exit 0

rooms=()
while IFS=, read -r machine _; do
  [[ "$machine" == machine || -z "$machine" ]] || rooms+=("$machine")
done < rsc/machine/machines.csv
# what the sessions' Write and Edit calls wrote under a memory directory, by path below it
written="$(grep -rhoE --include='*.jsonl' '"file_path": ?"[^"]*/memory/[^"]+"' "${roots[@]}" | while IFS= read -r hit; do
  hit="${hit%\"}"
  echo "${hit##*/memory/}"
done | sort -u || true)"

fact_of() {
  local rel="$1" stem="${1%.md}" room
  for room in ${rooms[@]+"${rooms[@]}"}; do
    [[ "$stem" == *".$room" ]] && { echo "${stem%".$room"}.md"; return; }
  done
  echo "$rel"
}

unwritten=()
for dir in "${dirs[@]}"; do
  while IFS= read -r file; do
    grep -qxF -- "$(fact_of "${file#"$dir"/}")" <<< "$written" || unwritten+=("$file")
  done < <(find "$dir" -type f ! -name .DS_Store | sort)
done
if (( ${#unwritten[@]} )); then
  named="$(printf '%s, ' "${unwritten[@]}")"
  echo "FAIL: no stored or staged session wrote ${named%, } - no log holds their text; keep each elsewhere or remove it by hand, then run $SELF again" >&2
  exit 1
fi

for dir in "${dirs[@]}"; do
  dispose "$dir"
done
