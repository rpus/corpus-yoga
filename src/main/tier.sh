# shellcheck shell=bash
# tier.sh — the tiers as a declared contract (issues/702), the shell twin of src/main/tier.py.
# Every script reads its code root from CORPUS_YOGA_ROOT, which the launcher hands every run it
# starts (issues/1173); the one fact it lacks is which layout its
# tiers are read from, and that is one name: CORPUS_YOGA_REHEARSAL, a rehearsal's stamp,
# (CORPUS_YOGA_ACT, CORPUS_YOGA_STAMP and CORPUS_YOGA_LOG are the launcher's: the act it
# dispatched, that act's stamp and the record it tees the act into - read here alone, by
# stamp_of and record_of, and only by the act they name - src/main/tier.py, issues/708, issues/912)
# names the stage as the root, unset the checkout's; CORPUS_YOGA_DEV_GATE, while the
# dev gate runs, the directory under tmp/ it keeps its own data and stage under (issues/1171). DATA_ROOT is
# that root, DATA_DIR, CACHE_ROOT, LOGS_ROOT and TMP_DIR its data, cache, logs and tmp; STAGE_DIR is the
# stage, laid out as the checkout is (issues/1163), and FETCH_DIR the fetched copies whatever tiers
# are in force (issues/1170). tier_path turns a declared repo-relative path (data/..., cache/...,
# logs/..., tmp/..., stage/...) into the tier's. Sourced, never run; the names are the sourcing script's own, never exported.
TIER_REPO="${CORPUS_YOGA_ROOT:?the repository root, which corpus-yoga hands every run it starts}"
# the stage, one directory (issues/1171): the room's, or the dev gate's own while it runs
# shellcheck disable=SC2034  # the sourcing script's to use
STAGE_DIR="${CORPUS_YOGA_DEV_GATE:-$TIER_REPO}/stage"
# its tiers, as the checkout's are laid out (issues/1163)
# shellcheck disable=SC2034  # the sourcing script's to use
STAGE_INPUT="$STAGE_DIR/data/input"
# shellcheck disable=SC2034  # the sourcing script's to use
STAGE_OUTPUT="$STAGE_DIR/data/output"
# shellcheck disable=SC2034  # the sourcing script's to use
STAGE_CACHE="$STAGE_DIR/cache"
# shellcheck disable=SC2034  # the sourcing script's to use
STAGE_LOGS="$STAGE_DIR/logs"
# shellcheck disable=SC2034  # the sourcing script's to use
STAGE_TMP="$STAGE_DIR/tmp"
# shellcheck disable=SC2034  # the sourcing script's to use
FETCH_DIR="$TIER_REPO/fetch"
# a rehearsal's data, cache, logs and tmp are the stage's own; the dev gate's its own directory (issues/1134)
if [[ -n "${CORPUS_YOGA_REHEARSAL:-}" ]]; then DATA_ROOT="$STAGE_DIR"; else DATA_ROOT="${CORPUS_YOGA_DEV_GATE:-$TIER_REPO}"; fi
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
# dispatched none; the pid the run's own, so that corpus-yoga tmp names what a run that died left there. No directory
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

# cache_of <input path>: what the run derives from an input lives at the input's own address under
# cache/pipeline (issues/1192) - its path under the input tree, the store's or the stage's,
# re-rooted, a session's .jsonl dropped - as tier.py's cache_of.
cache_of() {
  local path="$1" root real rel=''
  for root in "$DATA_DIR/input" "$STAGE_INPUT"; do
    case "$path" in "$root"/*) rel="${path#"$root"/}"; break ;; esac
    real="$(cd "$root" 2>/dev/null && pwd -P)" || continue
    case "$path" in "$real"/*) rel="${path#"$real"/}"; break ;; esac
  done
  [[ -n "$rel" ]] || { echo "cache_of: $path is under no input tree" >&2; return 1; }
  echo "$CACHE_ROOT/pipeline/${rel%.jsonl}"
}

tier_path() {
  case "$1" in
    data|data/*|cache|cache/*|logs|logs/*|tmp|tmp/*) echo "$DATA_ROOT/$1" ;;
    stage) echo "$STAGE_DIR" ;;
    stage/*) echo "$STAGE_DIR/${1#stage/}" ;;
    *) echo "$TIER_REPO/$1" ;;
  esac
}
