# shellcheck shell=bash
# tier.sh — the tiers as a declared contract (issues/702), the shell twin of src/main/tier.py.
# Every script computes its code root itself; the one fact it lacks is which layout its
# tiers are read from, and that is one name: CORPUS_YOGA_REHEARSAL, a rehearsal's stamp,
# (CORPUS_YOGA_ACT, CORPUS_YOGA_STAMP and CORPUS_YOGA_LOG are the launcher's: the act it
# dispatched, that act's stamp and the record it tees the act into - read here alone, by
# stamp_of and record_of, and only by the act they name - src/main/tier.py, issues/708, issues/912)
# names the stage's scratch root, stage/<actor>/scratch, unset the checkout's. DATA_ROOT is
# that root, DATA_DIR, CACHE_ROOT, LOGS_ROOT and TMP_DIR its data, cache, logs and tmp; STAGE_DIR is the actor's
# stage, stage/<actor>, STAGE_SCRATCH its scratch and FETCH_DIR the fetched copies whatever tiers
# are in force (issues/1170). tier_path turns a declared repo-relative path (data/..., cache/...,
# logs/..., tmp/...) into the tier's. Sourced, never run; the names are the sourcing script's own, never exported.
_tier_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIER_REPO="${_tier_dir%/src/main}"
# the actor's stage under stage/ (issues/1133): the usr actor's, stage/usr, wherever
# CORPUS_YOGA_ACTOR names no other - stage/dev the one other
case "${CORPUS_YOGA_ACTOR:-usr}" in
  usr|dev) _tier_actor="${CORPUS_YOGA_ACTOR:-usr}" ;;
  *) echo "tier.sh: CORPUS_YOGA_ACTOR names ${CORPUS_YOGA_ACTOR}, no actor of usr, dev" >&2; exit 1 ;;
esac
# shellcheck disable=SC2034  # the sourcing script's to use
STAGE_DIR="$TIER_REPO/stage/$_tier_actor"
# shellcheck disable=SC2034  # the sourcing script's to use
STAGE_SCRATCH="$STAGE_DIR/scratch"
# shellcheck disable=SC2034  # the sourcing script's to use
FETCH_DIR="$TIER_REPO/fetch"
# a rehearsal's data, cache, logs and tmp are its stage's scratch; so are the dev actor's always (issues/1134)
if [[ -n "${CORPUS_YOGA_REHEARSAL:-}" || "$_tier_actor" == dev ]]; then DATA_ROOT="$STAGE_SCRATCH"; else DATA_ROOT="$TIER_REPO"; fi
# shellcheck disable=SC2034  # the sourcing script's to use
DATA_DIR="$DATA_ROOT/data"
# shellcheck disable=SC2034  # the sourcing script's to use
CACHE_ROOT="$DATA_ROOT/cache"
LOGS_ROOT="$DATA_ROOT/logs"
TMP_DIR="$DATA_ROOT/tmp"
# where acts are logged: the room's history, or beneath the check the dev gate names (issues/1030)
# shellcheck disable=SC2034  # the sourcing script's to use
if [[ -n "${CORPUS_YOGA_GATE_CHECK:-}" ]]; then LOGS_DIR="$TIER_REPO/logs/test/run/$CORPUS_YOGA_GATE_CHECK"; else LOGS_DIR="$LOGS_ROOT"; fi

# scratch_file <name>, scratch_dir <name>: a disposable file or directory a run keeps only
# while it runs (issues/906), made directly under tmp/ and named <act>.<name>.<pid>.<random> - the
# act the launcher dispatched, <command>.<verb>, or the running script's own name, $0, where it
# dispatched none, never SELF, which every helper a script sources declares over the script's own;
# the pid the run's own, so that corpus-yoga tmp names what a run that died left there. No directory
# is made for a run, so none is left empty when its files go (issues/1170). No script calls mktemp
# but through these: nothing disposable is written outside the tree.
_run_prefix() {
  local act="${CORPUS_YOGA_ACT:-}" script="${0##*/}"
  if [[ -n "$act" ]]; then echo "$TMP_DIR/${act// /.}"; else echo "$TMP_DIR/${script%.*}"; fi
}
scratch_file() {
  mkdir -p "$TMP_DIR" && mktemp "$(_run_prefix).$1.$$.XXXXXX"
}
scratch_dir() {
  mkdir -p "$TMP_DIR" && mktemp -d "$(_run_prefix).$1.$$.XXXXXX"
}

# stamp_of <command> <verb>: the act's stamp - the launcher's where it dispatched this act,
# a fresh one otherwise. record_of <command> <verb>: the act's record, the launcher's tee,
# where the launcher dispatched this act, nothing otherwise; no verb writes into it (issues/912).
stamp_of() {
  if [[ "${CORPUS_YOGA_ACT:-}" == "$1 $2" && -n "${CORPUS_YOGA_STAMP:-}" ]]; then echo "$CORPUS_YOGA_STAMP"
  else date -u '+%Y-%m-%dT%H%M%SZ'; fi
}
record_of() {
  if [[ "${CORPUS_YOGA_ACT:-}" == "$1 $2" ]]; then echo "${CORPUS_YOGA_LOG:-}"; fi
}

tier_path() {
  case "$1" in
    data|data/*|cache|cache/*|logs|logs/*|tmp|tmp/*) echo "$DATA_ROOT/$1" ;;
    *) echo "$TIER_REPO/$1" ;;
  esac
}
