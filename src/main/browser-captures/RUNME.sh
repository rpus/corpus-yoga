#!/usr/bin/env bash
# Validate browser-captured API JSON files against the apiConversation schema.
#
# Usage:
#   ./src/main/browser-captures/RUNME.sh
#   ./src/main/browser-captures/RUNME.sh --browser-captures ext/browser-captures/claude
#   ./src/main/browser-captures/RUNME.sh --browser-capture ext/browser-captures/claude/<uuid>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

parse_args() {
  browser_capture=""
  browser_captures="$REPO_DIR/ext/browser-captures/claude"
  new_claude_scrape=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --browser-capture)  browser_capture="$2";  shift 2 ;;
      --browser-captures) if [[ $# -gt 1 && "${2-}" != --* ]]; then browser_captures="$2"; shift 2; else shift; fi ;;
      --new-claude-scrape)    new_claude_scrape=1; shift ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 [--browser-captures <path>] | --browser-capture <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

run_one() {
  local input_dir="${1%/}"
  "$SCRIPT_DIR/claude/validate.sh" --browser-capture "$input_dir"
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$browser_capture" ]]; then
    run_one "$(cd "$browser_capture" && pwd)"
  else
    if [[ ! -d "$browser_captures" ]]; then
      echo "no captures in $browser_captures (populate via ./RUNME.sh --capture-from-browser)"
      exit 0
    fi
    local root; root="$(cd "$browser_captures" && pwd)"
    local found=0
    for d in "$root"/*/; do
      [[ -d "$d" ]] || continue
      found=1
      run_one "$d"
    done
    if [[ $found -eq 0 ]]; then
      echo "no captures in $root"
    else
      # render api JSON -> markdown always; diff it against the DOM scrape only when claude was
      # scraped this run (--new-claude-scrape) -- otherwise there is no scrape md to compare against.
      "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/model/project_markdown.py" \
        --browser-captures "$root"
      # gemini's scrapes ARE markdown already -- copy them into the presentation tree
      # beside claude's projections (gen/markdown/{claude,gemini}), anchoring each turn
      # heading for navigability; a slug collision gets the conversation id prefixed.
      "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/copy_gemini_markdown.py"
      # capture-health report against the fresh projections (informational — the
      # compare gate below decides pass/fail; PREP.sh printed the pre-run baseline)
      "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit_captures.py" \
        --browser-captures "$REPO_DIR/ext/browser-captures" \
        --api "$REPO_DIR/gen/markdown/claude" || true
      if [[ -n "$new_claude_scrape" ]]; then
        "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/compare_markdown.py" \
          --api "$REPO_DIR/gen/markdown/claude" --scrape "$root"
      fi
    fi
  fi
}

main "$@"
