#!/usr/bin/env bash
# Capture conversations from browser-reachable providers into
# data/input/<provider>/chat/browser-{API,DOM}/, via Safari (open and logged in).
# The `yoga browser` target.
#
# Two mechanisms: API (claude only) and DOM (--DOM; slow, a page walk). Each provider
# runs the intersection with what it supports, so gemini REQUIRES --DOM to do anything.
#
# Usage:
#   yoga browser                                 # free, local: are the captures any good?
#   yoga browser check                           # LIVE: which conversations have moved on?
#   yoga browser capture                         # claude API (gemini needs --DOM)
#   yoga browser capture --DOM                   # claude API + DOM, gemini DOM
#   yoga browser capture --provider claude --DOM # one provider, both mechanisms
#   yoga browser capture --provider claude --id <id>   # one conversation
#
#   --id requires --provider: an id's shape cannot say whose it is.
#   `check` is a verb, not a flag on the bare noun, because it drives Safari — bare is
#   status: free and local.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# The bare-noun default: the capture-health audit, read-only. Shows what is captured
# and what is missing without touching Safari or writing anything — the same audit
# `capture` runs first, run alone. There is no `status` verb; the bare noun IS it.
status() {
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_captures.py" \
    --input "$REPO_DIR/data/input" \
    --api "$REPO_DIR/data/output/markdown/claude/chat/conversations"
}

main() {
  case "${1-}" in
    capture) shift ;;
    # `check` is audit_captures --live: the question the filesystem audit cannot answer,
    # and until now the CLI had no route to it at all — the flag existed, the surface did
    # not. Read-only (it fetches listings and compares; it writes nothing), so `check`,
    # the verb that already means exactly that on supersede and xref.
    check)
      shift
      [[ $# -eq 0 ]] || { echo "yoga browser check takes no arguments (got: $1)" >&2; exit 1; }
      exec "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_captures.py" \
        --input "$REPO_DIR/data/input" \
        --api "$REPO_DIR/data/output/markdown/claude/chat/conversations" --live ;;
    '') status; exit $? ;;   # bare noun → status (read-only), never the scrape
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "Usage: $0 capture [--provider claude|gemini] [--DOM] [--id <id>] | check  (--help for details)" >&2; exit 1 ;;
  esac
  local provider="" dom="" id=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --provider)
        case "${2-}" in
          claude|gemini) provider="$2"; shift 2 ;;
          *) echo "error: --provider takes claude | gemini (got: ${2-})" >&2; exit 1 ;;
        esac ;;
      --DOM) dom="1"; shift ;;
      --id)
        case "${2-}" in
          ''|--*) echo "error: --id takes a conversation id (got: ${2-})" >&2; exit 1 ;;
          *) id="$2"; shift 2 ;;
        esac ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Usage: $0 capture [--provider claude|gemini] [--DOM] [--id <id>]"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done

  # An id belongs to exactly one provider, and its SHAPE cannot say which: a claude chat
  # uuid and a code-session uuid are both 36 chars. So --id is meaningless without
  # --provider, and asking is better than guessing wrong and capturing into the wrong tree.
  if [[ -n "$id" && -z "$provider" ]]; then
    echo "error: --id names one conversation, and an id's shape does not say whose — pass --provider claude|gemini with it" >&2
    exit 1
  fi

  if [[ "$provider" == "gemini" && -z "$dom" ]]; then
    echo "error: gemini has no API — its only mechanism is the DOM scrape; pass --DOM (slow: a scrape walk per conversation)" >&2
    exit 1
  fi

  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  mkdir -p "$REPO_DIR/data/input/claude/chat/browser-API"
  mkdir -p "$REPO_DIR/data/input/gemini/chat/browser-DOM"

  # Capture-health baseline before the run — the before/after delta lands in the same
  # log. Suspects here are the reason to capture, not an error.
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_captures.py" \
    --input "$REPO_DIR/data/input" \
    --api "$REPO_DIR/data/output/markdown/claude/chat/conversations" || true
  # Capture each in-scope provider regardless of another failing, then surface a
  # non-zero exit if any did.
  local rc=0
  if [[ -z "$provider" || "$provider" == "claude" ]]; then
    "$SCRIPT_DIR/safari_capture.sh" --provider claude ${dom:+--scrape} ${id:+--id "$id"} || rc=$?
  fi
  if [[ -z "$provider" || "$provider" == "gemini" ]]; then
    if [[ -n "$dom" ]]; then
      "$SCRIPT_DIR/safari_capture.sh" --provider gemini ${id:+--id "$id"} || rc=$?
    else
      echo "gemini: skipped — no API mechanism; pass --DOM for the scrape"
    fi
  fi
  return $rc
}

main "$@"
