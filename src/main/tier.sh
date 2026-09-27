# shellcheck shell=bash
# tier.sh — the tiers as a declared contract (#702), the shell twin of src/main/tier.py:
# DATA_DIR and TMP_DIR, each defaulting to the checkout's own, CORPUS_YOGA_DATA and
# CORPUS_YOGA_TMP naming other tiers; STAGE_DIR the checkout's stage. tier_path turns a
# declared repo-relative path (data/..., tmp/...) into the tier's. Sourced, never run.
# The three names are this script's own, derived each time the twin is sourced and never
# exported: the contract's environment is CORPUS_YOGA_DATA and CORPUS_YOGA_TMP alone, and a
# child that needs the tiers sources the twin itself.
_tier_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIER_REPO="${_tier_dir%/src/main}"
DATA_DIR="${CORPUS_YOGA_DATA:-$TIER_REPO/data}"
TMP_DIR="${CORPUS_YOGA_TMP:-$TIER_REPO/tmp}"
# shellcheck disable=SC2034  # the sourcing script's to use, like the two above
STAGE_DIR="$TIER_REPO/tmp/stage"

tier_path() {
  case "$1" in
    data)   echo "$DATA_DIR" ;;
    data/*) echo "$DATA_DIR/${1#data/}" ;;
    tmp)    echo "$TMP_DIR" ;;
    tmp/*)  echo "$TMP_DIR/${1#tmp/}" ;;
    *)      echo "$TIER_REPO/$1" ;;
  esac
}
