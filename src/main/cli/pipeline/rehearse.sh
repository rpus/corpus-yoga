#!/usr/bin/env bash
# rehearse.sh (corpus-yoga pipeline rehearse) — the pipelines over the stage, the checkout's
# own code run over the stage's scratch tiers, and the record of what it saw and judged
# (#687, #702, #815).
#
# Usage:
#   corpus-yoga pipeline rehearse   # every pipeline over everything staged
#
# A rehearsal is the stage's judgement, whole: it takes no extent, and its record,
# tmp/stage/rehearsal.json, is the verdict for every staged unit until the next rehearsal
# replaces it whole. A pipeline with nothing staged skips and says so. The store is large
# and one pipeline's run is the usual act there; the stage is small by construction and
# gets one judgement.
#
# The run is corpus-yoga pipeline run with CORPUS_YOGA_REHEARSAL=<stamp>, the one name the
# tier contract (src/main/tier.py) resolves to the scratch tiers, tmp/stage/scratch, so
# every script reads and writes the scratch alone: no copy of the code, no copy of the
# room's cache or output, no link into data/input. The scratch is made afresh for each run -
# data/input a link to tmp/stage/input, the shared tier the captures wrote; data/output the
# preview of the staged units; tmp/cache their validation - and what it holds is grist. The
# record is what a reader reads (src/main/rehearsal.py): before the run, the digest of every
# staged unit is taken; after it, the verdicts the run wrote are reduced with them into the
# record, written whole, with the stamp, the commit, the Signature and the run's exit. The
# log, tmp/logs/pipeline/rehearse/<stamp>.log, shares the stamp.

set -euo pipefail

SELF='src/main/cli/pipeline/rehearse.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${_self_dir%/"${SELF%/*}"}"
[[ "${REPO_ROOT}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_ROOT/src/main/tier.sh"
# shellcheck source=src/main/provider.sh
source "$REPO_ROOT/src/main/provider.sh"   # provider_signature - the log header's triad (#704)

main() {
  local stamp log head
  # the stage's word first (#721): a rehearsal judges a stage the stage reads as whole, and
  # no pipeline is shown an incomplete unit - the janitor is the remedy
  "$REPO_ROOT/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import corpus; sys.exit(corpus.refuse_rehearsal())' "$REPO_ROOT/src/main"
  stamp="$(date -u '+%Y-%m-%dT%H%M%SZ')"
  log="$TMP_DIR/logs/pipeline/rehearse/$stamp.log"
  rm -rf "$TMP_STAGE_SCRATCH"
  mkdir -p "$TMP_STAGE/input" "$TMP_STAGE_SCRATCH/data/output" "$TMP_STAGE_SCRATCH/tmp" "$(dirname "$log")"
  ln -s ../../input "$TMP_STAGE_SCRATCH/data/input"   # tmp/stage/scratch/data/input -> tmp/stage/input
  head="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo '(no git)')"
  {
    echo "pipeline rehearse - $stamp - $(provider_signature "$REPO_ROOT") - $head"
    echo "corpus-yoga pipeline rehearse"
    echo "rehearse: tmp/stage/scratch - corpus-yoga pipeline run with CORPUS_YOGA_REHEARSAL=$stamp (src/main/tier.py: data and tmp under that directory, its input tmp/stage/input); then tmp/stage/rehearsal.json, the record"
    echo
    "$REPO_ROOT/src/run_python_script.sh" "$REPO_ROOT/src/main/rehearsal.py" begin "$stamp" || exit 1
    local status=0
    CORPUS_YOGA_REHEARSAL="$stamp" "$REPO_ROOT/corpus-yoga" pipeline run || status=$?
    echo
    "$REPO_ROOT/src/run_python_script.sh" "$REPO_ROOT/src/main/rehearsal.py" end "$stamp" "$status" || exit 1
    exit "$status"
  } 2>&1 | tee "$log"
  return "${PIPESTATUS[0]}"
}

main "$@"
