#!/usr/bin/env bash
# rsc/migration/1133.sh - the stage is one per actor, the reader's at tmp/stage/usr (issues/1133):
# each entry the room's tmp/stage holds from before - its input, scratch and rehearsal.json, and
# whatever else stood beside them - moves into tmp/stage/usr, where the usr actor's acts now read
# and write it and the stage status names what nothing reads. The scratch's data/input, a link to
# ../../input, follows the input it names.
set -euo pipefail
SELF='rsc/migration/1133.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

[[ -d tmp/stage ]] || exit 0
for entry in tmp/stage/*; do
  [[ -e "$entry" || -L "$entry" ]] || continue
  case "${entry##*/}" in usr|dev) continue ;; esac
  move "$entry" "tmp/stage/usr/${entry##*/}"
done
