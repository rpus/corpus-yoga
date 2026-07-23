#!/usr/bin/env bash
# Run the chat-exports pipeline against one or all exports.
#
# Usage:
#   ./src/main/chat-exports/RUNME.sh --chat-export  data/input/claude/chat/bulk-export/data-<...>
#   ./src/main/chat-exports/RUNME.sh --chat-exports data/input/claude/chat/bulk-export
#   ./src/main/chat-exports/RUNME.sh --plan   # print the ordered step list; run nothing
#
# The step lists below (run_one, run_tail) are the ONE authority on order:
# --plan prints exactly the lists that execute (see src/main/steps.sh).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CACHE_DIR="$REPO_DIR/tmp/cache/chat-exports"

# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"

parse_args() {
  chat_export=""
  chat_exports=""
  plan="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export)       chat_export="$2";      shift 2 ;;
      --chat-exports)      chat_exports="$2";     shift 2 ;;
      --plan)              plan="1";              shift   ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --chat-export <path> | --chat-exports <path> | --plan"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ "$plan" == "0" && -z "$chat_export" && -z "$chat_exports" ]]; then
    echo "Usage: $0 --chat-export <path/to/single-export>"
    echo "       $0 --chat-exports <path/to/chat-exports>"
    echo
    echo "Options:"
    echo "  --plan   print the ordered step list; run nothing"
    echo "Pass --help for more information."
    exit 1
  fi
}

run_one() {
  local batch="${1%/}"
  # No blanket wipe of tmp/cache/<batch>: each stage owns (wipes or overwrites) its own
  # output subtree. A blanket wipe would destroy the validation memoisation logs,
  # forcing full revalidation every run. (The paid captures are out of reach either
  # way — they live in data/output/dashboard/, not under tmp/cache/.)
  local have_captures="0"
  if [[ -d "$REPO_DIR/data/input/claude/chat/browser-API" ]]; then have_captures="1"; fi

  step validate           "$SCRIPT_DIR/validate.sh" --chat-export "$batch"
  # archive_components: the batch's non-conversation components (memories/projects/
  # users) verbatim into tmp/cache/<batch>/ — the cache dir is then the complete record of
  # the four-component snapshot, and compare_batches reads all four from that root
  step archive_components "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/archive_components.py" --chat-export "$batch"
  step extract_files      "$SCRIPT_DIR/extract_files.sh" --chat-export "$batch"
  step extract_heredocs   "$SCRIPT_DIR/extract_heredocs.sh" --chat-export "$batch"
  # inference is no longer per-batch: the dashboard's captures are the durable
  # single-source data/output/dashboard/ (refreshed deliberately by `yoga dashboard
  # capture`), which present reads. Nothing paid runs on every export now.
  step present            "$SCRIPT_DIR/present.sh" --chat-export "$batch"
  step audit_files        "$SCRIPT_DIR/audit_files.sh" --chat-export "$batch"
  # atomise_bulk: split the bulk array into verbatim per-conversation json/ pieces
  # (validated vs the Conversation definition); project_markdown renders them to
  # markdown/, beside this batch's validation/ output.
  step atomise_bulk       "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/atomise_bulk.py" --bulk-export "$batch"
  step project_markdown   "$REPO_DIR/src/run_python_script.sh" \
    "$REPO_DIR/src/main/model/project_markdown.py" --bulk-export "$batch"
  # compare_sources: live-api captures and this bulk export should project to
  # identical markdown for shared conversations. A difference is legitimate when a
  # conversation progressed after the export snapshot — hence never gates; the
  # report keeps what-agrees-with-what visible in every run log.
  step_if_ok "$have_captures" 'when live captures exist' \
       compare_sources    "$REPO_DIR/src/run_python_script.sh" \
    "$REPO_DIR/src/main/model/compare_sources.py" \
    --browser-api "$REPO_DIR/data/input/claude/chat/browser-API" --bulk-export "$batch"
}

# run_tail: the once-after-all-batches REDUCE — steps that fold the whole corpus rather
# than process one snapshot. This is where the yoga nouns live, and only here: a step is
# eligible for a command (a help.csv `step` row) iff it is a corpus-wide operation
# meaningful to invoke standalone — which is precisely the run_tail character. A run_one
# per-batch stage (`--chat-export <batch>`) is internal machinery; giving it a noun would
# be claiming a batch-scoped map step is a standalone corpus operation. The three here —
# memories, summaries, supersede — are exactly cli.steps().
run_tail() {
  # memories: every distinct memory state deposits into the durable
  # data/output/memories/ (snapshot-time-keyed, content-deduplicated — the memory document
  # is mutable and lossy between exports, and bulk exports are its only log) and the
  # timeline renders to data/output/markdown/claude/chat/memories/. A deposited state is the
  # licence to delete a memories-divergent batch; the verdict below stays unprejudiced.
  step memories "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/accumulate_memories.py" sync
  # summaries: the same deposit discipline per conversation — a summary is
  # a per-snapshot oracle reading (stochastic; lossy between exports, and captures
  # refresh in place), so every distinct reading deposits into
  # data/output/markdown/claude/chat/summaries/<conversation>/ (export-snapshot-time-keyed,
  # content-deduplicated). A deposited reading is the licence to delete a
  # summaries-divergent batch; the verdict below stays unprejudiced.
  step summaries "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/accumulate_summaries.py" sync
  # supersede: a batch is a synchronised snapshot of FOUR components
  # (conversations, memories, projects, users), licensed as FIVE — a conversation's
  # summary is a per-snapshot oracle reading, checked as its own component — each
  # put through the same unprejudiced unit/atom subset check; no component is
  # assumed append-only or mutable; a batch is deletable iff EVERY component is
  # superseded (their lattice join). Also compares the latest batch against the
  # live-capture corpus per conversation: capture-ahead is normal post-snapshot
  # growth; capture-stale names conversations to recapture in place. Divergence is
  # a fact, not an error.
  step_ok supersede  "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/compare_batches.py" check \
    --chat-exports-cache "$CACHE_DIR" --browser-api "$REPO_DIR/data/input/claude/chat/browser-API"
}

print_plan() {
  echo "chat-exports steps — per batch (data/input/claude/chat/bulk-export/data-*/ in name order):"
  run_one '<batch>'
  echo "then once, after all batches:"
  run_tail
}

main() {
  parse_args "$@"
  if [[ "$plan" == "1" ]]; then print_plan; exit 0; fi
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$chat_export" ]]; then
    run_one "$(cd "$chat_export" && pwd)"
  else
    if [[ ! -d "$chat_exports" ]]; then
      echo "no bulk exports in $chat_exports (download from https://claude.ai/settings/data-privacy-controls)"
      exit 0
    fi
    for d in "$(cd "$chat_exports" && pwd)"/data-*/; do
      [[ -d "$d" ]] || continue
      run_one "$d"
    done
  fi

  run_tail
}

main "$@"
