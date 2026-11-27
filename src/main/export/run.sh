#!/usr/bin/env bash
# Run the export pipeline against one or all exports.
#
# Usage:
#   src/main/export/run.sh --item  data/input/claude/chat/bulk-export/data-<...>
#   src/main/export/run.sh --input data/input/claude/chat/bulk-export
#   src/main/export/run.sh --input data/input/claude/chat/bulk-export --collate
#   src/main/export/run.sh --plan   # print the ordered step list; run nothing
#
# Each batch is read on its own; --collate reads each against the rest of the corpus, then
# folds them all. The step lists below (run_one, collate_head, collate_one, run_tail) are the ONE authority on order:
# --plan prints exactly the lists that execute (see src/main/steps.sh).

set -euo pipefail

SELF='src/main/export/run.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_DIR/src/main/tier.sh"

# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"

# The cross-source join reads browser's claude input at ITS declared root — the
# sibling's pipeline.json is the one committed authority for that path.
API_CAPTURE="$(resolve_input "$(tier_path "$(jq -r .input "$REPO_DIR/src/main/browser/pipeline.json")")" \
  "$REPO_DIR/src/main/browser/pipeline.json" claude)"

parse_args() {
  chat_export=""
  chat_exports=""
  plan="0"
  collate="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --item)              chat_export="$2";      shift 2 ;;
      --input)             chat_exports="$2";     shift 2 ;;
      --plan)              plan="1";              shift   ;;
      --collate)           collate="1";           shift   ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --item <path> | --input <path> | --plan"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ "$plan" == "0" && -z "$chat_export" && -z "$chat_exports" ]]; then
    echo "Usage: $0 --item <path/to/single-export>"
    echo "       $0 --input <path/to/bulk-export>"
    echo
    echo "Options:"
    echo "  --plan   print the ordered step list; run nothing"
    echo "Pass --help for more information."
    exit 1
  fi
}

run_one() {
  local batch="${1%/}"
  # No blanket wipe of cache/<batch>: each stage owns (wipes or overwrites) its own
  # output subtree. A blanket wipe would destroy the validation memoisation logs,
  # forcing full revalidation every run. (The paid captures are out of reach either
  # way — they live in data/output/indexing/, not under cache/.)
  map step validate           "$SCRIPT_DIR/validate.sh" --export "$batch"
  # archive_components: the batch's non-conversation components (memories/projects/
  # users) verbatim into cache/<batch>/ — the cache dir is then the complete record of
  # the four-component snapshot
  map step archive_components "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/archive_components.py" --export "$batch"
  map step extract_files      "$SCRIPT_DIR/extract_files.sh" --export "$batch"
  map step extract_heredocs   "$SCRIPT_DIR/extract_heredocs.sh" --export "$batch"
  # atomise_bulk: split the bulk array into verbatim per-conversation json/ pieces
  # (validated vs the Conversation definition)
  map step atomise_bulk       "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/atomise_bulk.py" --bulk-export "$batch"
  # render: each piece's markdown under its name, at the batch's cache address, which the
  # collate dresses and places (issues/1196)
  map step render             "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/render.py" --bulk-export "$batch"
}

# collate_head: once, before any batch is collated.
collate_head() {
  # current: nothing is placed older than its input - every unit's run output was made from
  # the input as it stands, or the collate stops here, naming what the run is owed (issues/1183)
  reduce step current "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validation_audit.py" --owed export
}

# collate_one: one batch read against what else the corpus holds - the paid indexing captures
# and downloaded artifacts, the live captures - so a batch's result here depends on the rest.
collate_one() {
  local batch="${1%/}"
  local have_captures="0"
  if [[ -d "$API_CAPTURE" ]]; then have_captures="1"; fi
  # project_markdown: the run's renderings placed in markdown/, beside this batch's
  # validation/ output, each frontmatter saying how current it is against the live captures
  reduce step project_markdown   "$REPO_DIR/src/run_python_script.sh" \
    "$REPO_DIR/src/main/project_markdown.py" --bulk-export "$batch"
  # inference is not per-batch: the dashboard's captures are the durable
  # single-source data/output/indexing/ (refreshed deliberately by `corpus-yoga indexing
  # capture`), which present reads. Nothing paid runs on every export.
  reduce step present            "$SCRIPT_DIR/present.sh" --export "$batch"
  # audit_files: the batch's files against the presentation's tables, which present writes
  reduce step audit_files        "$SCRIPT_DIR/audit_files.sh" --export "$batch"
  # compare_sources: the append-only invariant across export surfaces (issues/535, the
  # dev gate's former cross_sources check, spoken here once): a conversation in
  # both a bulk export and the live captures projects to identical turns, or the
  # export is a prefix of the capture (it progressed after the snapshot). The
  # capture being a prefix of the EXPORT is a stale capture; divergence inside the
  # shared prefix is a projection defect or corruption - both FAIL and gate.
  reduce step_if "$have_captures" 'when live captures exist' \
       compare_sources    "$REPO_DIR/src/run_python_script.sh" \
    "$REPO_DIR/src/main/compare_sources.py" \
    --api-capture "$API_CAPTURE" --bulk-export "$batch"
}

# run_tail: the once-after-all-batches REDUCE of the collate — steps that fold the whole corpus rather
# than process one snapshot. This is where the corpus-yoga nouns live, and only here: a step is
# eligible for a command (a declared `step`) iff it is a corpus-wide operation
# meaningful to invoke standalone — which is precisely the run_tail character. A run_one
# per-batch stage (`--item <batch>`) is internal machinery; giving it a noun would
# be claiming a batch-scoped map step is a standalone corpus operation. The two here —
# memories, summaries — are this pipeline's cli.steps(); the comparison after them is a
# step and no command.
run_tail() {
  # memories: every distinct memory state deposits into the durable
  # data/output/memories/ (snapshot-time-keyed, content-deduplicated — the memory document
  # is mutable and lossy between exports, and bulk exports are its only log) and the
  # timeline renders to data/output/markdown/claude/chat/memories/. A deposited state is the
  # licence to delete a memories-divergent batch; the verdict below stays unprejudiced.
  reduce step memories "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/memories.py" deposit
  # summaries: the same deposit discipline per conversation — a summary is
  # a per-snapshot oracle reading (stochastic; lossy between exports, and captures
  # refresh in place), so every distinct reading deposits into
  # data/output/markdown/claude/chat/summaries/<conversation>/ (export-snapshot-time-keyed,
  # content-deduplicated). A deposited reading is the licence to delete a
  # summaries-divergent batch; the verdict below stays unprejudiced.
  reduce step summaries "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/summaries.py" deposit
  # compare_captures: the latest batch against the live-capture corpus per
  # conversation: capture-ahead is normal post-snapshot growth; capture-stale names
  # conversations to recapture in place. Divergence is a fact, not an error. Whether an
  # earlier batch is held whole within a later one is the store's reading, by the
  # export's atoms (issues/743), and its disposal the store's janitor in the corpus tail (issues/744).
  reduce step_ok compare_captures "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/compare_captures.py" --api-capture "$API_CAPTURE"
}

print_plan() {
  if [[ "$collate" == "0" ]]; then
    echo "export steps — per batch (data/input/claude/chat/bulk-export/data-*/ in name order):"
    run_one '<batch>'
    return
  fi
  echo "export steps — collate mode (--collate), first, once:"
  collate_head
  echo "then per batch in name order:"
  collate_one '<batch>'
  echo "then once, after all batches:"
  run_tail
}

main() {
  parse_args "$@"
  if [[ "$plan" == "1" ]]; then print_plan; exit 0; fi
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$chat_export" ]]; then
    run_one "$(cd "$chat_export" && pwd)"
    return 0
  fi
  local each=run_one
  [[ "$collate" == "0" ]] || each=collate_one
  if [[ ! -d "$chat_exports" ]]; then
    echo "no bulk exports in $chat_exports (download from https://claude.ai/settings/data-privacy-controls)"
    exit 0
  fi
  [[ "$collate" == "0" ]] || collate_head
  for d in "$(cd "$chat_exports" && pwd)"/data-*/; do
    [[ -d "$d" ]] || continue
    "$each" "$d"
  done

  [[ "$collate" == "0" ]] || run_tail
}

main "$@"
