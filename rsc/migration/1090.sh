#!/usr/bin/env bash
# rsc/migration/1090.sh - the corpus holds no agent memory (issues/1090): each memory directory
# the store or the stage holds under claude's machine transport is disposed of. Bare, a line per
# directory with its files and bytes - the disposal record, read before the apply; applied, the
# same lines, which the migration's log keeps.
set -euo pipefail
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

for root in data/input/claude/code/machine-transport tmp/stage/input/claude/code/machine-transport; do
  [[ -d "$root" ]] || continue
  while IFS= read -r dir; do
    dispose "$dir"
  done < <(find "$root" -mindepth 3 -maxdepth 3 -type d -name memory | sort)
done
