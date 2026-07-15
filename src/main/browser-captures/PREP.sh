#!/usr/bin/env bash
# Capture conversations from browser-reachable providers into input/<provider>/chat/browser-{API,DOM}/,
# via Safari (requires it open and logged in to the provider sites). The `yoga browser` target.
#
# The mechanism set defaults to {API}; --DOM adds the DOM scrape. Each provider runs
# the intersection with what it supports: claude has both (API JSON per conversation;
# DOM only with --DOM, feeding compare_markdown); gemini is DOM-only, so it REQUIRES
# --DOM to do anything — the asymmetry, and the scrape's duration, deserve a flag.
# A capture-health audit runs first, so the before/after delta lands in the same log.
#
# Usage:
#   yoga browser capture                              # claude API (gemini needs --DOM)
#   yoga browser capture --DOM                        # claude API + DOM, gemini DOM
#   yoga browser capture --provider claude --DOM      # claude API + DOM (feeds compare_markdown)
#   yoga browser capture --provider gemini --DOM      # gemini DOM scrape only
#   (src/main/browser-captures/PREP.sh takes the same verb and flags)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

main() {
  case "${1-}" in
    capture) shift ;;
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "Usage: $0 capture [--provider claude|gemini] [--DOM]  (--help for details)" >&2; exit 1 ;;
  esac
  local provider="" dom=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --provider)
        case "${2-}" in
          claude|gemini) provider="$2"; shift 2 ;;
          *) echo "error: --provider takes claude | gemini (got: ${2-})" >&2; exit 1 ;;
        esac ;;
      --DOM) dom="1"; shift ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Usage: $0 capture [--provider claude|gemini] [--DOM]"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ "$provider" == "gemini" && -z "$dom" ]]; then
    echo "error: gemini has no API — its only mechanism is the DOM scrape; pass --DOM (slow: a scrape walk per conversation)" >&2
    exit 1
  fi

  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  mkdir -p "$REPO_DIR/input/claude/chat/browser-API"
  mkdir -p "$REPO_DIR/input/gemini/chat/browser-DOM"

  # Capture-health baseline before the run — the before/after delta lands in the same
  # log. Suspects here are the reason to capture, not an error.
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_captures.py" \
    --input "$REPO_DIR/input" \
    --api "$REPO_DIR/output/markdown/claude/chat/conversations" || true
  # Capture each in-scope provider regardless of another failing, then surface a
  # non-zero exit if any did.
  local rc=0
  if [[ -z "$provider" || "$provider" == "claude" ]]; then
    "$SCRIPT_DIR/safari_capture.sh" --agent claude ${dom:+--scrape} || rc=$?
  fi
  if [[ -z "$provider" || "$provider" == "gemini" ]]; then
    if [[ -n "$dom" ]]; then
      "$SCRIPT_DIR/safari_capture.sh" --agent gemini || rc=$?
    else
      echo "gemini: skipped — no API mechanism; pass --DOM for the scrape"
    fi
  fi
  return $rc
}

main "$@"
