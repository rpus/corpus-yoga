#!/usr/bin/env bash
# Run the chat-exports pipeline against one or all exports.
#
# Usage:
#   ./src/main/chat-exports/RUNME.sh --chat-export  ext/chat-exports/data-<...>
#   ./src/main/chat-exports/RUNME.sh --chat-exports ext/chat-exports
#   ./src/main/chat-exports/RUNME.sh --chat-exports ext/chat-exports --pay-for-inference

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
OUTPUT_DIR="$REPO_DIR/gen/chat-exports"

parse_args() {
  chat_export=""
  chat_exports=""
  pay_for_inference="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export)       chat_export="$2";      shift 2 ;;
      --chat-exports)      chat_exports="$2";     shift 2 ;;
      --pay-for-inference) pay_for_inference="1"; shift   ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --chat-export <path> | --chat-exports <path> [--pay-for-inference]"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$chat_export" && -z "$chat_exports" ]]; then
    echo "Usage: $0 --chat-export <path/to/single-export>"
    echo "       $0 --chat-exports <path/to/chat-exports>"
    echo
    echo "Options:"
    echo "  --pay-for-inference   also run infer_tables.sh (requires ANTHROPIC_API_KEY in env)"
    echo "Pass --help for more information."
    exit 1
  fi
}

run_one() {
  local input_dir="${1%/}"

  # No blanket wipe of gen/<batch>: each stage owns (wipes or overwrites) its own
  # output subtree. A blanket wipe would destroy the validation memoisation logs
  # (forcing full revalidation every run) and the durable paid inferred/ tables,
  # which by design persist across unpaid runs.

  "$SCRIPT_DIR/validate.sh"         --chat-export "$input_dir"
  # archive the batch's non-conversation components (memories/projects/users) verbatim
  # into gen/<batch>/ — the gen dir is then the complete record of the four-component
  # snapshot, and compare_batches reads all four from that one root
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/archive_components.py" \
    --chat-export "$input_dir"
  "$SCRIPT_DIR/extract_files.sh"    --chat-export "$input_dir"
  "$SCRIPT_DIR/extract_heredocs.sh" --chat-export "$input_dir"

  if [[ "$pay_for_inference" == "1" ]]; then
    "$SCRIPT_DIR/infer_tables.sh" --chat-export "$input_dir"
  fi

  "$SCRIPT_DIR/present.sh"     --chat-export "$input_dir"
  "$SCRIPT_DIR/audit_files.sh" --chat-export "$input_dir"
  # split the bulk array into verbatim per-conversation json/ pieces (validated vs the Conversation
  # definition), then render them to markdown/, beside this batch's validation/ output.
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/atomise_bulk.py" \
    --bulk-export "$input_dir"
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/model/project_markdown.py" \
    --bulk-export "$input_dir"

  # cross-source sanity (informational): live-api captures and this bulk export should
  # project to identical markdown for shared conversations. A difference is legitimate
  # when a conversation progressed after the export snapshot — hence no gating; the
  # report keeps what-agrees-with-what visible in every run log.
  if [[ -d "$REPO_DIR/ext/browser-captures/claude" ]]; then
    "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/model/compare_sources.py" \
      --browser-captures "$REPO_DIR/ext/browser-captures/claude" \
      --bulk-export "$input_dir" || true
  fi
}

main() {
  parse_args "$@"
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

  # supersession report (informational): a batch is a synchronised snapshot of FOUR
  # components (conversations, memories, projects, users), each put through the same
  # unprejudiced unit/atom subset check — no component is assumed append-only or
  # mutable; a batch is deletable iff EVERY component is superseded (their lattice
  # join). Also compares the latest batch against the live-capture corpus per
  # conversation: capture-ahead is normal post-snapshot growth; capture-stale names
  # conversations to recapture in place. Divergence is a fact, not an error.
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/compare_batches.py" \
    --chat-exports-gen "$OUTPUT_DIR" \
    --captures "$REPO_DIR/ext/browser-captures/claude" || true
}

main "$@"
