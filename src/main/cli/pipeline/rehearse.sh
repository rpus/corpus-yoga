#!/usr/bin/env bash
# rehearse.sh (corpus-yoga pipeline rehearse) — the pipelines over the stage, the checkout's
# own code run over a rehearsal's own tiers (#687, #702).
#
# Usage:
#   corpus-yoga pipeline rehearse   # every pipeline over everything staged
#
# A rehearsal is the stage's judgement, whole: it takes no extent, so the newest
# rehearsal is the verdict for every staged unit, an older stamp is an older judgement
# whole, and the stamps are one linear order. A pipeline with nothing staged skips and
# says so. The store is large and one pipeline's run is the usual act there; the stage
# is small by construction and gets one judgement.
#
# A rehearsal is an act with an anchor - a commit, an extent, the staged bytes it judged -
# and what it derives is evidence, so each has a directory of its own, tmp/stage/rehearsal/
# <stamp>, and a log of its own, tmp/logs/pipeline/rehearse/<stamp>.log, one stamp for both.
# <stamp>/data/input is a link to tmp/stage/input, the shared tier the captures wrote;
# <stamp>/data/output is the preview of the staged units; <stamp>/tmp/cache holds their
# verdicts. The run inside is corpus-yoga pipeline run with CORPUS_YOGA_REHEARSAL=<stamp>,
# the one name the tier contract (src/main/tier.py) resolves to those tiers, so every
# script reads and writes the rehearsal alone: no copy of the code, no copy of the room's
# cache or output, no link into data/input. The promote verbs read a named rehearsal, the
# newest by default; corpus-yoga stage lists them, and stage clean removes them as the
# disposal of evidence it is.

set -euo pipefail

SELF='src/main/cli/pipeline/rehearse.sh'
_self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${_self_dir%/"${SELF%/*}"}"
[[ "${REPO_ROOT}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_ROOT/src/main/tier.sh"

main() {
  local stamp rehearsal log room head
  # the stage's word first (#721): a rehearsal judges a stage the stage reads as whole, and
  # no pipeline is shown an incomplete unit - the janitor is the remedy
  "$REPO_ROOT/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import corpus; sys.exit(corpus.refuse_rehearsal())' "$REPO_ROOT/src/main"
  stamp="$(date -u '+%Y-%m-%dT%H%M%SZ')"
  rehearsal="$TMP_STAGE/rehearsal/$stamp"
  log="$TMP_DIR/logs/pipeline/rehearse/$stamp.log"
  mkdir -p "$TMP_STAGE/input" "$rehearsal/data/output" "$rehearsal/tmp" "$(dirname "$log")"
  ln -s ../../../input "$rehearsal/data/input"   # tmp/stage/rehearsal/<stamp>/data/input -> tmp/stage/input
  # the log's header is the rehearsal's record: the stamp, the room, the commit, then the
  # command as typed - what corpus-yoga stage reads
  room="$(cat "$REPO_ROOT/machine-name.txt" 2>/dev/null || echo '(unbound)')"
  head="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo '(no git)')"
  {
    echo "pipeline rehearse — $stamp · room: $room · $head"
    echo "corpus-yoga pipeline rehearse"
    echo "rehearse: tmp/stage/rehearsal/$stamp - corpus-yoga pipeline run with CORPUS_YOGA_REHEARSAL=$stamp (src/main/tier.py: data and tmp under that directory, its input tmp/stage/input)"
    echo
    CORPUS_YOGA_REHEARSAL="$stamp" "$REPO_ROOT/corpus-yoga" pipeline run
  } 2>&1 | tee "$log"
  return "${PIPESTATUS[0]}"
}

main "$@"
