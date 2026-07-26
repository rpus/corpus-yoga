#!/usr/bin/env bash
# Capture conversations from browser-reachable providers into
# data/input/<provider>/chat/browser-{API,DOM}/, via Safari (open and logged in).
# The `yoga browser` target.
#
# Scope is two independent restrictions, and the run is their intersection. Neither adds:
# a provider has the mechanisms it has (claude API and DOM, gemini DOM), and a restriction
# can only take some away. Unrestricted means all of it.
#
# Usage:
#   yoga browser                                      # free, local: are the captures any good?
#   yoga browser check                                # LIVE: which conversations have moved on?
#   yoga browser capture                              # every provider, every mechanism it has
#   yoga browser capture --mechanism API              # only what an API can give: claude
#   yoga browser capture --provider gemini            # gemini, by the DOM walk it has
#   yoga browser capture --provider claude --id <id>  # one conversation
#
#   --id requires --provider: an id's shape cannot say whose it is.
#   Restrictions that intersect to nothing are reported, not defaulted around.
#   YOGA_NO_SEND=1 refuses every outward call: a capture has no scratch form, so refusing
#   it is the only way to exercise these paths without reaching the account.

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
    # the verb that already means exactly that on supersede and xref. A verb and not a
    # flag on the bare noun, because it drives Safari: bare is status, free and local.
    check)
      shift
      [[ $# -eq 0 ]] || { echo "yoga browser check takes no arguments (got: $1)" >&2; exit 1; }
      exec "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_captures.py" \
        --input "$REPO_DIR/data/input" \
        --api "$REPO_DIR/data/output/markdown/claude/chat/conversations" --live ;;
    '') status; exit $? ;;   # bare noun → status (read-only), never a capture
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "Usage: $0 capture [--provider claude|gemini] [--mechanism API|DOM] [--id <id>] | check  (--help for details)" >&2; exit 1 ;;
  esac
  local provider="" mechanism="" id=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --provider)
        case "${2-}" in
          claude|gemini) provider="$2"; shift 2 ;;
          *) echo "error: --provider takes claude | gemini (got: ${2-})" >&2; exit 1 ;;
        esac ;;
      --mechanism)
        case "${2-}" in
          API|DOM) mechanism="$2"; shift 2 ;;
          *) echo "error: --mechanism takes API | DOM (got: ${2-})" >&2; exit 1 ;;
        esac ;;
      --id)
        case "${2-}" in
          ''|--*) echo "error: --id takes a conversation id (got: ${2-})" >&2; exit 1 ;;
          *) id="$2"; shift 2 ;;
        esac ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Usage: $0 capture [--provider claude|gemini] [--mechanism API|DOM] [--id <id>]"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done

  # An id belongs to exactly one provider, and its SHAPE cannot say which: a claude chat
  # uuid and a code-session uuid are both 36 chars. So --id is meaningless without
  # --provider, and asking is better than guessing wrong and capturing into the wrong tree.
  if [[ -n "$id" && -z "$provider" ]]; then
    echo "error: --id names one conversation, and an id's shape does not say whose — pass --provider claude|gemini with it" >&2
    exit 1
  fi

  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  mkdir -p "$REPO_DIR/data/input/claude/chat/browser-API"
  mkdir -p "$REPO_DIR/data/input/gemini/chat/browser-DOM"

  # The extent, read off the one declaration: which providers, by which mechanisms.
  # Two restrictions can intersect to nothing, and that is an answer — reported with
  # what does exist, never silently substituted with a default.
  local scope
  scope="$("$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/safari_capture.py" --scope \
    ${provider:+--provider "$provider"} ${mechanism:+--mechanism "$mechanism"})"
  if [[ -z "$scope" ]]; then
    echo "error: --provider $provider --mechanism $mechanism selects nothing to capture; what exists:" >&2
    "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/safari_capture.py" --scope >&2
    exit 1
  fi

  # Capture-health baseline before the run — the before/after delta lands in the same
  # log. Suspects here are the reason to capture, not an error.
  "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_captures.py" \
    --input "$REPO_DIR/data/input" \
    --api "$REPO_DIR/data/output/markdown/claude/chat/conversations" || true
  # Capture each provider the restrictions leave in scope, regardless of another
  # failing, then surface a non-zero exit if any did. The scope comes from
  # safari_capture.py's declaration, so this loop holds no second copy of which
  # provider has which mechanism — the pair a restriction leaves empty simply does
  # not appear here.
  local rc=0 p mechs
  while read -r p mechs; do
    [[ -n "$p" ]] || continue
    echo "$p: capturing by ${mechs//+/ and }"
    "$SCRIPT_DIR/safari_capture.sh" --provider "$p" ${mechanism:+--mechanism "$mechanism"} \
      ${id:+--id "$id"} || rc=$?
  done <<< "$scope"
  return $rc
}

main "$@"
