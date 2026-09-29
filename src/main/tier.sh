# shellcheck shell=bash
# tier.sh — the tiers as a declared contract (#702), the shell twin of src/main/tier.py.
# Every script computes its code root itself; the one fact it lacks is which layout its
# tiers are read from, and that is one name: CORPUS_YOGA_REHEARSAL, a rehearsal's stamp,
# names the rehearsal's root under tmp/stage/rehearsal, unset the checkout's. DATA_ROOT is
# that root, DATA_DIR and TMP_DIR its data and tmp; TMP_STAGE is the checkout's stage, a
# constant. tier_path turns a declared repo-relative path (data/..., tmp/...) into the
# tier's. Sourced, never run; the names are the sourcing script's own, never exported.
_tier_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIER_REPO="${_tier_dir%/src/main}"
# shellcheck disable=SC2034  # the sourcing script's to use
TMP_STAGE="$TIER_REPO/tmp/stage"
if [[ -n "${CORPUS_YOGA_REHEARSAL:-}" ]]; then DATA_ROOT="$TIER_REPO/tmp/stage/rehearsal/$CORPUS_YOGA_REHEARSAL"; else DATA_ROOT="$TIER_REPO"; fi
DATA_DIR="$DATA_ROOT/data"
TMP_DIR="$DATA_ROOT/tmp"

tier_path() {
  case "$1" in
    data)   echo "$DATA_DIR" ;;
    data/*) echo "$DATA_DIR/${1#data/}" ;;
    tmp)    echo "$TMP_DIR" ;;
    tmp/*)  echo "$TMP_DIR/${1#tmp/}" ;;
    *)      echo "$TIER_REPO/$1" ;;
  esac
}
