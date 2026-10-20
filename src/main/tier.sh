# shellcheck shell=bash
# tier.sh — the tiers as a declared contract (issues/702), the shell twin of src/main/tier.py.
# Every script computes its code root itself; the one fact it lacks is which layout its
# tiers are read from, and that is one name: CORPUS_YOGA_REHEARSAL, a rehearsal's stamp,
# (CORPUS_YOGA_ACT, CORPUS_YOGA_STAMP and CORPUS_YOGA_LOG are the launcher's: the act it
# dispatched, that act's stamp and the record it tees the act into - read here alone, by
# stamp_of and record_of, and only by the act they name - src/main/tier.py, issues/708, issues/912)
# names the stage's scratch root, tmp/stage/scratch, unset the checkout's. DATA_ROOT is
# that root, DATA_DIR and TMP_DIR its data and tmp; TMP_STAGE is the checkout's stage, a
# constant, and TMP_STAGE_SCRATCH the scratch whatever tiers are in force. tier_path turns
# a declared repo-relative path (data/..., tmp/...) into the tier's. Sourced, never run; the names are the sourcing script's own, never exported.
_tier_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIER_REPO="${_tier_dir%/src/main}"
# shellcheck disable=SC2034  # the sourcing script's to use
TMP_STAGE="$TIER_REPO/tmp/stage"
# shellcheck disable=SC2034  # the sourcing script's to use
TMP_STAGE_SCRATCH="$TIER_REPO/tmp/stage/scratch"
if [[ -n "${CORPUS_YOGA_REHEARSAL:-}" ]]; then DATA_ROOT="$TMP_STAGE_SCRATCH"; else DATA_ROOT="$TIER_REPO"; fi
DATA_DIR="$DATA_ROOT/data"
TMP_DIR="$DATA_ROOT/tmp"

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
    data)   echo "$DATA_DIR" ;;
    data/*) echo "$DATA_DIR/${1#data/}" ;;
    tmp)    echo "$TMP_DIR" ;;
    tmp/*)  echo "$TMP_DIR/${1#tmp/}" ;;
    *)      echo "$TIER_REPO/$1" ;;
  esac
}
