#!/usr/bin/env bash
# Capture conversations from browser-reachable providers into
# data/input/<provider>/chat/browser-{API,DOM}/, via Safari (open and logged in).
# The `yoga browser` target.
#
# Scope is two independent restrictions, intersected. Neither adds: a provider has the
# mechanisms it has (claude API — DOM retired, #418; gemini DOM); a restriction only takes some away.
#
# Usage:
#   yoga browser                                      # free, local: are the captures any good?
#   yoga browser capture                              # every provider, every mechanism it has
#   yoga browser capture --mechanism API              # only what an API can give: claude
#   yoga browser capture --provider gemini            # gemini, by the DOM walk it has
#   yoga browser capture --provider claude --dry-run  # discovery + extent, nothing captured
#   yoga browser capture --provider claude --id <id>  # one conversation
#
#   --id requires --provider: an id's shape cannot say whose it is, and restrictions that
#   intersect to nothing are reported rather than defaulted around. --dry-run fetches
#   listings (a send) and captures nothing: the extent, then stop.
#   YOGA_NO_SEND=1 refuses every outward call: a capture has no scratch form, so refusing
#   it is the only way to exercise these paths without reaching the account.

set -euo pipefail

SELF='src/main/cli/browser/browser.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

# The bare-noun default: the capture-health audit, read-only. Shows what is captured
# and what is missing without touching Safari or writing anything — the same audit
# `capture` runs first, run alone. There is no `status` verb; the bare noun IS it.
status() {
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/pipeline/browser-captures/audit_captures.py" \
    --input "$REPO_DIR/data/input" \
    --api "$REPO_DIR/data/output/markdown/claude/chat/conversations"
}

main() {
  case "${1-}" in
    capture) shift ;;
    '') status; exit $? ;;   # bare noun → status (read-only), never a capture
    --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "Usage: yoga browser capture [--provider claude|gemini] [--mechanism API|DOM] [--id <id>] [--dry-run]  (yoga browser -h for details)" >&2; exit 1 ;;
  esac
  local provider="" mechanism="" id="" dry_run="" files=""
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
      --dry-run) dry_run="1"; shift ;;
      --files)   files="1";   shift ;;
      --id)
        case "${2-}" in
          ''|--*) echo "error: --id takes a conversation id (got: ${2-})" >&2; exit 1 ;;
          *) id="$2"; shift 2 ;;
        esac ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Usage: yoga browser capture [--provider claude|gemini] [--mechanism API|DOM] [--id <id>] [--dry-run]"; echo "Pass yoga browser -h for more information."; exit 1 ;;
    esac
  done

  # An id belongs to exactly one provider, and its SHAPE cannot say which: a claude chat
  # uuid and a code-session uuid are both 36 chars. So --id is meaningless without
  # --provider, and asking is better than guessing wrong and capturing into the wrong tree.
  if [[ -n "$id" && -z "$provider" ]]; then
    echo "error: --id names one conversation, and an id's shape does not say whose — pass --provider claude|gemini with it" >&2
    exit 1
  fi
  if [[ -n "$files" && "$provider" != "claude" ]]; then
    echo "error: --files is a claude acquisition (the API captures name the handles) — pass --provider claude" >&2
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

  # No audit preamble (#418): the capture-health audit is bare `yoga browser`'s
  # own output, on demand — re-running it before every capture duplicated what
  # the bare noun already answers, and its bulk (consistency QA of
  # already-captured data) is not about what this run will do. The capture's
  # bracket is its EXTENT — captured / never-captured — computed by
  # safari_capture.py from the discovery the run performs anyway; --dry-run is
  # that first call run alone (G19: discovery + extent, nothing captured),
  # forwarded below like any other restriction.
  #
  # The run logs are still named HERE (#412/#413): browser.sh opens each with
  # the "capturing by" line and hands it down via --run-log for the capture to
  # append — one anchored record per provider, preamble or no preamble.
  local stamp providers=() provider_mechs=() logs=() p mechs
  stamp="$(date -u '+%Y-%m-%dT%H%M%SZ')"
  while read -r p mechs; do
    [[ -n "$p" ]] || continue
    providers+=("$p")
    provider_mechs+=("$mechs")
    logs+=("$REPO_DIR/tmp/logs/browser/capture/$p/$stamp.log")
    mkdir -p "$REPO_DIR/tmp/logs/browser/capture/$p"
  done <<< "$scope"
  # Capture each provider the restrictions leave in scope, regardless of another
  # failing, then surface a non-zero exit if any did. The scope comes from
  # safari_capture.py's declaration, so this loop holds no second copy of which
  # provider has which mechanism — the pair a restriction leaves empty simply does
  # not appear here.
  local rc=0 i=0
  for p in ${providers[@]+"${providers[@]}"}; do
    mechs="${provider_mechs[$i]}"
    echo "$p: capturing by ${mechs//+/ and }" | tee -a "${logs[$i]}"
    "$SCRIPT_DIR/safari_capture.sh" --run-log "${logs[$i]}" --provider "$p" ${mechanism:+--mechanism "$mechanism"} \
      ${id:+--id "$id"} ${dry_run:+--dry-run} ${files:+--files} || rc=$?
    i=$((i + 1))
  done
  return $rc
}

main "$@"
