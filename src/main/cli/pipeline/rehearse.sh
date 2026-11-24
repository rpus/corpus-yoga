#!/usr/bin/env bash
# rehearse.sh (corpus-yoga pipeline rehearse) — the pipelines over the stage, the checkout's
# own code run over the stage's scratch tiers, and the record of what it saw and judged
# (issues/687, issues/702, issues/815).
#
# Usage:
#   corpus-yoga pipeline rehearse   # every pipeline over everything staged
#
# A rehearsal is the stage's judgement, whole: it takes no extent, and its record,
# tmp/stage/usr/rehearsal.json, is the verdict for every staged unit until the next rehearsal
# replaces it whole. A pipeline with nothing staged skips and says so. The store is large
# and one pipeline's run is the usual act there; the stage is small by construction and
# gets one judgement.
#
# The run is the pipeline noun's run, a step of this verb at one narration depth deeper, so that
# its lines and its effect stand beneath the rehearsal's one verdict (issues/1090), with
# CORPUS_YOGA_REHEARSAL=<stamp>, the one name the
# tier contract (src/main/tier.py) resolves to the scratch tiers, tmp/stage/usr/scratch, so
# every script reads and writes the scratch alone: no copy of the code, no copy of the
# room's cache or output, no link into data/input. The scratch is made afresh for each run -
# data/input a link to tmp/stage/usr/input, the shared tier the captures wrote; data/output the
# preview of the staged units; tmp/cache their validation - and what it holds is grist. The
# record is what a reader reads (src/main/rehearsal.py): before the run, the digest of every
# staged unit is taken; after it, the verdicts the run wrote are reduced with them into the
# record, written whole, with the stamp, the commit, the Signature and the run's exit. The
# record, tmp/logs/pipeline/rehearse/<stamp>.log, the launcher's tee, shares the stamp (issues/708).

set -euo pipefail

SELF='src/main/cli/pipeline/rehearse.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${_self_dir%/"${SELF%/*}"}"
[[ "${REPO_ROOT}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_ROOT/src/main/tier.sh"
# shellcheck source=src/main/provider.sh
source "$REPO_ROOT/src/main/provider.sh"   # provider_signature - the log header's triad (issues/704)
# shellcheck source=src/main/report.sh
source "$REPO_ROOT/src/main/report.sh"   # sentence - the one face a sentence is said through (issues/909)

main() {
  local stamp
  # the stage's word first (issues/996): each incomplete unit is said as passed over - the
  # janitor's, never a pipeline's input - and the whole units are judged
  "$REPO_ROOT/src/run_python_script.sh" -c 'import sys; import corpus; sys.exit(corpus.pass_over())'
  # the rehearsal's stamp is the launcher's where it ran the verb (issues/708), so the record,
  # tmp/logs/pipeline/rehearse/<stamp>.log, and the rehearsal record share it
  stamp="$(stamp_of pipeline rehearse)"
  rm -rf "$TMP_STAGE_SCRATCH"
  mkdir -p "$TMP_STAGE/input" "$TMP_STAGE_SCRATCH/data/output" "$TMP_STAGE_SCRATCH/tmp"
  ln -s ../../input "$TMP_STAGE_SCRATCH/data/input"   # tmp/stage/usr/scratch/data/input -> tmp/stage/usr/input
  echo "rehearse: $(phrase "tmp/stage/usr/scratch - corpus-yoga pipeline run with CORPUS_YOGA_REHEARSAL={stamp} (src/main/tier.py puts data and tmp under that directory, its input tmp/stage/usr/input); then tmp/stage/usr/rehearsal.json, the record" stamp="$stamp")"
  echo
  "$REPO_ROOT/src/run_python_script.sh" "$REPO_ROOT/src/main/rehearsal.py" begin "$stamp" || return 1
  local status=0
  CORPUS_YOGA_REHEARSAL="$stamp" CORPUS_YOGA_NARRATION_DEPTH=$(( ${CORPUS_YOGA_NARRATION_DEPTH:-0} + 1 )) \
    "$REPO_ROOT/src/main/cli/pipeline/pipeline.sh" run || status=$?
  echo
  # the rehearsal's exit is its own verdict's (issues/1145): judged whole, whatever the run found
  "$REPO_ROOT/src/run_python_script.sh" "$REPO_ROOT/src/main/rehearsal.py" end "$stamp" "$status"
}

main "$@"
