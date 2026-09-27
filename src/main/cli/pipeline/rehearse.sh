#!/usr/bin/env bash
# rehearse.sh (corpus-yoga pipeline rehearse) — the pipelines over the stage, the checkout's
# own code run over the stage's tiers (#687, #702).
#
# Usage:
#   corpus-yoga pipeline rehearse [<pipeline>]   # every pipeline, or one by name, as run takes it
#
# The tiers are a declared contract (src/main/tier.py, src/main/tier.sh): the data tier
# and the tmp tier, each defaulting to the checkout's own. A rehearsal names the stage's -
# CORPUS_YOGA_DATA=tmp/stage/data, whose input the captures wrote; CORPUS_YOGA_TMP=
# tmp/stage/tmp - and runs corpus-yoga pipeline run with its tests stage skipped, so every
# script reads and writes the stage alone: no copy of the code, no copy of the room's cache
# or output, no link into data/input. The stage's tmp/cache then holds each staged unit's
# verdict at its cache address, which the promote verbs read; the stage's data/output is
# the staged units' own projection. corpus-yoga stage clean removes what a rehearsal
# derived; tmp/stage/data/input is the captures' and is only read.

set -euo pipefail

SELF='src/main/cli/pipeline/rehearse.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${_self_dir%/"${SELF%/*}"}"
[[ "${REPO_ROOT}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_ROOT/src/main/tier.sh"

main() {
  mkdir -p "$STAGE_DIR/data/input" "$STAGE_DIR/data/output" "$STAGE_DIR/tmp"
  echo "rehearse: corpus-yoga pipeline run$* over the stage's tiers - CORPUS_YOGA_DATA=tmp/stage/data CORPUS_YOGA_TMP=tmp/stage/tmp (src/main/tier.py)"
  echo
  CORPUS_YOGA_DATA="$STAGE_DIR/data" CORPUS_YOGA_TMP="$STAGE_DIR/tmp" CORPUS_YOGA_REHEARSAL=1 "$REPO_ROOT/corpus-yoga" pipeline run "$@"
}

main "$@"
