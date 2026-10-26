#!/usr/bin/env bash
# Validate gemini's DOM-capture scrapes against the markdownConversation family, each lifted by lean.py (issues/965).
#
# Usage:
#   src/main/pipeline/chat-capture/gemini/validate.sh --capture <path/to/id-directory>
#   src/main/pipeline/chat-capture/gemini/validate.sh --dom-capture <path/to/DOM-capture-root>
#
# Corpus mode prints one summary line for the captures that are current (the
# steady-state majority); a capture only gets its own lines when something was
# revalidated or failed.

set -euo pipefail

SELF='src/main/pipeline/chat-capture/gemini/validate.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_DIR/src/main/tier.sh"
LEAN_SCHEMA_DIR="$REPO_DIR/rsc/schema/pipeline/chat-capture/markdownConversation"   # the core both providers share (issues/965)
CACHE_DIR="$TMP_DIR/cache/chat-capture/gemini"
# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"   # dispatch/dispatch_done — next-free dispatch (issues/395)

validate_conversation() {
  local id_dir="${1%/}"
  local id; id="$(basename "$id_dir")"
  local out_dir="$CACHE_DIR/$id"
  local found=0 rc=0
  for md in "$id_dir"/*.md; do
    [[ -f "$md" ]] || continue
    found=1
    "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/pipeline/chat-capture/lean.py" "$md" "$out_dir/markdownConversation.json" || rc=$?
    "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
      "$out_dir/markdownConversation.json" "$LEAN_SCHEMA_DIR" "$out_dir/validation/markdownConversation" "$id" || rc=$?
  done
  if [[ "$found" -eq 0 ]]; then
    echo "  (no scrape found)"
  fi
  return $rc
}

validate_corpus() {
  local root="$1"
  local total=0 current=0 failed=0 rc out
  local dirs=() d
  for d in "$root"/*/; do
    [[ -d "$d" ]] || continue
    dirs+=("${d%/}")
  done
  # The captures validate via next-free dispatch (issues/395), each one's output
  # buffered; this loop reads the buffers in listing order and applies the same
  # fold the serial loop applied — the dispatch is invisible in the artifact.
  [[ ${#dirs[@]} -gt 0 ]] && dispatch validate_conversation "${dirs[@]}"
  local i=0
  while [[ "$i" -lt "${DISPATCH_N:-0}" ]]; do
    total=$((total + 1))
    out="$(cat "$DISPATCH_DIR/$i.out")"
    rc="$(cat "$DISPATCH_DIR/$i.rc" 2>/dev/null || echo 1)"
    # An all-current capture reports exactly one "… current — skipped" line;
    # fold those into the corpus summary and let everything else through.
    if [[ $rc -eq 0 && "$out" != *$'\n'* && "$out" == *'version(s) current - skipped' ]]; then
      current=$((current + 1))
    else
      [[ -n "$out" ]] && printf '%s\n' "$out"
      if [[ $rc -ne 0 ]]; then failed=1; fi
    fi
    i=$((i + 1))
  done
  [[ ${#dirs[@]} -gt 0 ]] && dispatch_done
  if [[ $total -eq 0 ]]; then
    echo "  no captures in $root"
  elif [[ $current -gt 0 ]]; then
    echo "  $current/$total capture(s) current - skipped"
  fi
  return $failed
}

parse_args() {
  capture_dir=""
  dom_capture=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --capture)  capture_dir="$2";  shift 2 ;;
      --dom-capture) dom_capture="$2"; shift 2 ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --capture <path> | --dom-capture <root>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$capture_dir" && -z "$dom_capture" ]]; then
    echo "Usage: $0 --capture <path/to/uuid-directory>"
    echo "       $0 --dom-capture <path/to/API-capture-root>"
    echo "Pass --help for more information."
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  if [[ -n "$capture_dir" ]]; then
    validate_conversation "$(cd "$capture_dir" && pwd)"
  else
    validate_corpus "$(cd "$dom_capture" && pwd)"
  fi
}

main "$@"
