#!/usr/bin/env bash
# rehearse.sh (corpus-yoga pipeline rehearse) — the pipelines over the stage, the checkout's
# own code run over a rehearsal's tiers (#687, #702).
#
# Usage:
#   corpus-yoga pipeline rehearse [<pipeline>]   # every pipeline, or one by name, as run takes it
#
# The tiers are a declared contract (src/main/tier.py, src/main/tier.sh): the data tier
# and the tmp tier, each defaulting to the checkout's own. A rehearsal is an act with an
# anchor - a commit, an extent, the staged bytes it judged - and what it derives is
# evidence, so each has a directory of its own, tmp/stage/rehearsal/<stamp>, named by the
# stamp of its log under tmp/logs/pipeline/rehearse: <stamp>/data/input is a link to
# tmp/stage/input, the shared tier the captures wrote before any rehearsal; <stamp>/data/
# output is its preview of the staged units; <stamp>/tmp/cache holds their verdicts. The
# run inside is corpus-yoga pipeline run with CORPUS_YOGA_DATA and CORPUS_YOGA_TMP bound to
# those and its tests stage skipped, so every script reads and writes the rehearsal alone:
# no copy of the code, no copy of the room's cache or output, no link into data/input.
# The promote verbs read a named rehearsal, the newest by default; corpus-yoga stage lists
# them and stage clean removes them, as the disposal of evidence it is.

set -euo pipefail

SELF='src/main/cli/pipeline/rehearse.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${_self_dir%/"${SELF%/*}"}"
[[ "${REPO_ROOT}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_ROOT/src/main/tier.sh"

main() {
  # the stamp is the launcher's log's (CORPUS_YOGA_LOG); run by path, a stamp of its own
  local stamp rehearsal
  if [[ -n "${CORPUS_YOGA_LOG:-}" ]]; then stamp="$(basename "$CORPUS_YOGA_LOG" .log)"; else stamp="$(date -u '+%Y-%m-%dT%H%M%SZ')"; fi
  rehearsal="$STAGE_DIR/rehearsal/$stamp"
  mkdir -p "$STAGE_DIR/input" "$rehearsal/data/output" "$rehearsal/tmp"
  ln -s ../../input "$rehearsal/data/input"
  echo "rehearse: tmp/stage/rehearsal/$stamp - corpus-yoga pipeline run$* with CORPUS_YOGA_DATA=tmp/stage/rehearsal/$stamp/data (input -> tmp/stage/input) and CORPUS_YOGA_TMP=tmp/stage/rehearsal/$stamp/tmp (src/main/tier.py)"
  echo
  CORPUS_YOGA_DATA="$rehearsal/data" CORPUS_YOGA_TMP="$rehearsal/tmp" CORPUS_YOGA_REHEARSAL=1 "$REPO_ROOT/corpus-yoga" pipeline run "$@"
}

main "$@"
