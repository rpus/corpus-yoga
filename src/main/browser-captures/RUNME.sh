#!/usr/bin/env bash
# Validate browser-captured API JSON files against the apiConversation schema.
#
# Usage:
#   ./src/main/browser-captures/RUNME.sh
#   ./src/main/browser-captures/RUNME.sh --browser-api input/claude/chat/browser-API
#   ./src/main/browser-captures/RUNME.sh --browser-capture input/claude/chat/browser-API/<uuid>
#   ./src/main/browser-captures/RUNME.sh --plan   # print the ordered step list; run nothing
#
# The step list below (run_corpus) is the ONE authority on order: --plan prints
# exactly the list that executes (see src/main/steps.sh).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"

parse_args() {
  browser_capture=""
  browser_api="$REPO_DIR/input/claude/chat/browser-API"
  browser_dom="$REPO_DIR/input/claude/chat/browser-DOM"
  compare_scrape="0"
  plan="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --browser-capture)  browser_capture="$2";  shift 2 ;;
      --browser-dom)      browser_dom="$2";      shift 2 ;;
      # --browser-captures is the eponymous pipeline flag the root ./RUNME.sh
      # constructs (run_pipeline passes --<pipeline-name>); alias of --browser-api
      --browser-api|--browser-captures) if [[ $# -gt 1 && "${2-}" != --* ]]; then browser_api="$2"; shift 2; else shift; fi ;;
      --compare-scrape)       compare_scrape="1"; shift ;;
      --plan)             plan="1"; shift ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 [--browser-api <path>] | --browser-capture <path> | --plan"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

run_one() {
  local input_dir="${1%/}"
  step validate "$SCRIPT_DIR/claude/validate.sh" --browser-capture "$input_dir"
}

run_corpus() {
  local root="${1%/}"
  # validate: announces itself once and folds the all-current captures into one
  # summary line, so a 95-capture steady state is one line
  step validate              "$SCRIPT_DIR/claude/validate.sh" --browser-api "$root"
  # project_markdown: render api JSON -> markdown always (no DOM scrape needed)
  step project_markdown      "$REPO_DIR/src/run_python_script.sh" \
    "$REPO_DIR/src/main/model/project_markdown.py" --browser-api "$root"
  # copy_gemini_markdown: gemini's scrapes ARE markdown already — copy them into the
  # presentation tree beside claude's projections (output/markdown/{claude,gemini}),
  # anchoring each turn heading; a slug collision gets the conversation id prefixed.
  step copy_gemini_markdown  "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/copy_gemini_markdown.py"
  # audit_captures: capture-health report against the fresh projections (the compare
  # gate below decides pass/fail; PREP.sh printed the pre-run baseline)
  step_ok audit_captures     "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/audit_captures.py" \
    --input "$REPO_DIR/input" \
    --api "$REPO_DIR/output/markdown/claude/chat/conversations"
  # compare_markdown: diff the projection against the DOM scrape only when asked —
  # a fresh scrape (yoga browser capture --provider claude --DOM) is what makes the
  # comparison meaningful; against the resting legacy scrapes it is noise.
  step_if "$compare_scrape" 'with --compare-scrape' \
       compare_markdown      "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/compare_markdown.py" \
    --api "$REPO_DIR/output/markdown/claude/chat/conversations" --scrape "$browser_dom"
}

print_plan() {
  echo "browser-captures steps — corpus mode (default):"
  run_corpus '<captures-root>'
  echo "single-capture mode (--browser-capture <dir>): the validate step only"
}

main() {
  parse_args "$@"
  if [[ "$plan" == "1" ]]; then print_plan; exit 0; fi
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$browser_capture" ]]; then
    run_one "$(cd "$browser_capture" && pwd)"
  else
    if [[ ! -d "$browser_api" ]]; then
      echo "no captures in $browser_api (populate via: yoga browser capture)"
      exit 0
    fi
    local root; root="$(cd "$browser_api" && pwd)"
    if ! compgen -G "$root/*/" > /dev/null; then
      echo "no captures in $root"
    else
      run_corpus "$root"
    fi
  fi
}

main "$@"
