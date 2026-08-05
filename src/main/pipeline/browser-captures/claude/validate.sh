#!/usr/bin/env bash
# Validate browser-capture conversations against the apiConversation schema.
#
# Usage:
#   src/main/pipeline/browser-captures/claude/validate.sh --browser-capture <path/to/uuid-directory>
#   src/main/pipeline/browser-captures/claude/validate.sh --browser-api <path/to/browser-API-root>
#
# Corpus mode prints one summary line for the captures that are current (the
# steady-state majority); a capture only gets its own lines when something was
# revalidated or failed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
SCHEMA_DIR="$REPO_DIR/rsc/schema/browser-captures/apiConversation"
CACHE_DIR="$REPO_DIR/tmp/cache/browser-captures/claude"
# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"   # fan_run/fan_done — the per-datum fan (#360)

validate_conversation() {
  local uuid_dir="${1%/}"
  local uuid; uuid="$(basename "$uuid_dir")"
  local out_dir="$CACHE_DIR/$uuid"

  # Return the validator's own rc explicitly: corpus mode calls this inside a
  # $(…) with a tested exit status, a context where set -e is suspended — an
  # implicit fall-through would end on the if below and report success even
  # over a crashed validator run.
  local found=0 rc=0
  for json in "$uuid_dir"/*.json; do
    [[ -f "$json" ]] || continue
    found=1
    "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
      "$json" "$SCHEMA_DIR" "$out_dir/validation/apiConversation" "$uuid" || rc=$?
  done

  if [[ "$found" -eq 0 ]]; then
    echo "  (no JSON files found)"
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
  # The captures validate YOGA_JOBS-wide (#360), each one's output buffered;
  # this loop reads the buffers in listing order and applies the same fold the
  # serial loop applied — the fan is invisible in the artifact.
  [[ ${#dirs[@]} -gt 0 ]] && fan_run validate_conversation "${dirs[@]}"
  local i=0
  while [[ "$i" -lt "${FAN_N:-0}" ]]; do
    total=$((total + 1))
    out="$(cat "$FAN_DIR/$i.out")"
    rc="$(cat "$FAN_DIR/$i.rc" 2>/dev/null || echo 1)"
    # An all-current capture reports exactly one "… current — skipped" line;
    # fold those into the corpus summary and let everything else through.
    if [[ $rc -eq 0 && "$out" != *$'\n'* && "$out" == *'version(s) current — skipped' ]]; then
      current=$((current + 1))
    else
      [[ -n "$out" ]] && printf '%s\n' "$out"
      if [[ $rc -ne 0 ]]; then failed=1; fi
    fi
    i=$((i + 1))
  done
  [[ ${#dirs[@]} -gt 0 ]] && fan_done
  if [[ $total -eq 0 ]]; then
    echo "  no captures in $root"
  elif [[ $current -gt 0 ]]; then
    echo "  $current/$total capture(s) current — skipped"
  fi
  return $failed
}

parse_args() {
  browser_capture=""
  browser_api=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --browser-capture)  browser_capture="$2";  shift 2 ;;
      --browser-api) browser_api="$2"; shift 2 ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --browser-capture <path> | --browser-api <root>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$browser_capture" && -z "$browser_api" ]]; then
    echo "Usage: $0 --browser-capture <path/to/uuid-directory>"
    echo "       $0 --browser-api <path/to/browser-API-root>"
    echo "Pass --help for more information."
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"
  if [[ -n "$browser_capture" ]]; then
    validate_conversation "$(cd "$browser_capture" && pwd)"
  else
    validate_corpus "$(cd "$browser_api" && pwd)"
  fi
}

main "$@"
