#!/usr/bin/env bash
# rsc/migration/1058.sh - a renamed checkout is one project in the room's live store
# (issues/1058): each project folder a former path of the checkout keyed, as
# rsc/naming/checkout_paths.csv declares the paths with ~ as this machine's home, is brought
# under the current path's key through the claude mount,
# ext/mnt/claude/code/machine-transport/<machine> - every entry of the former folder but its
# memory moved across, the former folder retired once nothing else stands in it. An agent's
# memory is the room's own, which no transport holds (issues/1090), so a memory folder is never
# moved, removed or compared: it stands where it is, and a former folder that holds it stays
# (issues/1092). A former folder's entry whose name the current folder already holds is
# released where the store holds it byte for byte - the transport store, under the room and the
# former key, is its record - and otherwise halts with the pair named.
set -euo pipefail
SELF='rsc/migration/1058.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

[[ -f machine-name.txt ]] || exit 0
mount="ext/mnt/claude/code/machine-transport/$(<machine-name.txt)"
record="data/input/claude/code/machine-transport/$(<machine-name.txt)"
[[ -d "$mount/." ]] || exit 0
# Claude Code's project key: the path with every character outside [A-Za-z0-9] as '-' (transport.project_key)
key() { local path="${1/#\~/$HOME}"; echo "${path//[^A-Za-z0-9]/-}"; }
current=""
formers=()
while IFS=, read -r path status _note; do
  case "$status" in
    current) current="$(key "$path")" ;;
    former) formers+=("$(key "$path")") ;;
  esac
done < <(tail -n +2 rsc/naming/checkout_paths.csv)
[[ -n "$current" ]] || { echo "FAIL: rsc/naming/checkout_paths.csv declares no current path" >&2; exit 1; }

for former in "${formers[@]}"; do
  from="$mount/$former"
  [[ -d "$from" && ! -L "$from" ]] || continue
  for entry in "$from"/*; do
    [[ -e "$entry" || -L "$entry" ]] || continue
    [[ "${entry##*/}" == memory ]] && continue
    if stands "$mount/$current/${entry##*/}"; then release "$entry" "$record/$former/${entry##*/}"; fi
    move "$entry" "$mount/$current/${entry##*/}"
  done
  [[ -e "$from/memory" || -L "$from/memory" ]] || retire "$from"
done
