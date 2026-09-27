#!/usr/bin/env bash
# rehearse.sh (corpus-yoga pipeline rehearse) — the pipelines over the store with this room's
# stage laid over it, in a room of the stage's own (#687).
#
# Usage:
#   corpus-yoga pipeline rehearse [<pipeline>]   # every pipeline, or one by name, as run takes it
#
# The room is tmp/stage/room: clones of src, rsc, the launcher and machine-name.txt (APFS
# clones - no bytes copied); a data/input that is the store with tmp/stage/input laid over
# it, as a tree of links (src/main/corpus.py view); a tmp/cache that is tmp/stage/cache,
# seeded from the room's tmp/cache; a data/output that is tmp/stage/output, seeded from
# the room's data/output. The run inside it is corpus-yoga pipeline run of that room, with
# its tests stage skipped (the dev gate is the checkout's), so every script derives its
# root as that room and writes the stage's tiers alone. The stage's cache then holds each
# staged unit's verdict at its cache address, which the promote verbs read; the stage's
# output is a preview of the corpus with the stage promoted. rm -rf tmp/stage/room
# tmp/stage/cache tmp/stage/output undoes the whole rehearsal; tmp/stage/input is the
# captures' and is only read.

set -euo pipefail

SELF='src/main/cli/pipeline/rehearse.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${_self_dir%/"${SELF%/*}"}"
[[ "${REPO_ROOT}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

STAGE="$REPO_ROOT/tmp/stage"
ROOM="$STAGE/room"

# cp -c clones on APFS; where a clone is impossible (another volume, an evicted iCloud
# file) it copies, and says nothing either way.
seed() {   # <source> <target>: the target replaced by a clone of the source, or made empty
  rm -rf "$2"
  if [[ -e "$1" ]]; then cp -RLc "$1" "$2"; else mkdir -p "$2"; fi
}

main() {
  echo "rehearse: tmp/stage/room ← src, rsc, corpus-yoga, machine-name.txt (clones of this checkout at $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo '(no git)'))"
  rm -rf "$ROOM"
  mkdir -p "$ROOM/data" "$ROOM/tmp"
  cp -Rc "$REPO_ROOT/src" "$ROOM/src"
  cp -Rc "$REPO_ROOT/rsc" "$ROOM/rsc"
  cp -c "$REPO_ROOT/corpus-yoga" "$ROOM/corpus-yoga"
  [[ -f "$REPO_ROOT/machine-name.txt" ]] && cp -c "$REPO_ROOT/machine-name.txt" "$ROOM/machine-name.txt"
  echo "rehearse: tmp/stage/cache ← tmp/cache; tmp/stage/output ← data/output (seeds, so that only the stage is judged anew)"
  seed "$REPO_ROOT/tmp/cache" "$STAGE/cache"
  seed "$REPO_ROOT/data/output" "$STAGE/output"
  ln -s "$STAGE/cache" "$ROOM/tmp/cache"
  ln -s "$STAGE/output" "$ROOM/data/output"
  "$REPO_ROOT/src/run_python_script.sh" "$REPO_ROOT/src/main/corpus.py" view "$ROOM/data/input"
  echo "rehearse: corpus-yoga pipeline run$* in tmp/stage/room"
  echo
  CORPUS_YOGA_REHEARSAL=1 "$ROOM/corpus-yoga" pipeline run "$@"
}

main "$@"
