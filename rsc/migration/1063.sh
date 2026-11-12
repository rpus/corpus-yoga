#!/usr/bin/env bash
# rsc/migration/1063.sh - a memory index holds no record of a merge (issues/1063): the lines
# `corpus-yoga agent install` wrote into a project's MEMORY.md around what it merged - the
# begin and end of a merge, and one line per file it wrote - are stripped from every project
# of the room's live claude store, through the mount
# ext/mnt/claude/code/machine-transport/<machine>; the index lines between them are kept.
set -euo pipefail
SELF='rsc/migration/1063.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

[[ -f machine-name.txt ]] || exit 0
mount="ext/mnt/claude/code/machine-transport/$(<machine-name.txt)"
[[ -d "$mount/." ]] || exit 0
for index in "$mount"/*/memory/MEMORY.md; do
  [[ -f "$index" && ! -L "${index%/MEMORY.md}" ]] || continue
  strip "$index" '<!-- merge:'
done
