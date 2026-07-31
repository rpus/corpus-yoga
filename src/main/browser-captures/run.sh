#!/usr/bin/env bash
# Validate browser-captured API JSON files against the apiConversation schema.
#
# Usage:
#   src/main/browser-captures/run.sh
#   src/main/browser-captures/run.sh --browser-api data/input/claude/chat/browser-API
#   src/main/browser-captures/run.sh --browser-capture data/input/claude/chat/browser-API/<uuid>
#   src/main/browser-captures/run.sh --plan   # print the ordered step list; run nothing
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
  browser_api="$REPO_DIR/data/input/claude/chat/browser-API"
  browser_dom="$REPO_DIR/data/input/claude/chat/browser-DOM"
  has_dom="0"
  plan="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --browser-capture)  browser_capture="$2";  shift 2 ;;
      --browser-dom)      browser_dom="$2";      shift 2 ;;
      # --browser-captures is the eponymous pipeline flag the root src/main/pipeline.sh
      # constructs (run_pipeline passes --<pipeline-name>); alias of --browser-api
      --browser-api|--browser-captures) if [[ $# -gt 1 && "${2-}" != --* ]]; then browser_api="$2"; shift 2; else shift; fi ;;
      --plan)             plan="1"; shift ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
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
  # presentation tree beside claude's projections (data/output/markdown/{claude,gemini}),
  # anchoring each turn heading; a slug collision gets the conversation id prefixed.
  step copy_gemini_markdown  "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/copy_gemini_markdown.py"
  # audit_captures: capture-health report against the fresh projections (the compare
  # gate below decides pass/fail; browser.sh printed the pre-run baseline)
  # set here, where browser_dom is final (a --browser-dom override lands before this)
  [[ -n "$(find "$browser_dom" -mindepth 2 -name '*.md' -print -quit 2>/dev/null)" ]] && has_dom="1"
  step_ok audit_captures     "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/audit_captures.py" \
    --input "$REPO_DIR/data/input" \
    --api "$REPO_DIR/data/output/markdown/claude/chat/conversations"
  # compare_markdown: diff the projection of the API capture against the DOM capture,
  # whenever there IS a DOM capture. It was opt-in behind --compare-scrape because every
  # difference read as a WARN with a remedy that could not fix it, so running it on resting
  # captures was noise. #61 removed that: a difference is now attributed — `API capture
  # missing` is a loss, `projection renders differently` is not — and severity follows, so
  # there is nothing left to opt out of. The comparison is local, free, and each side is the
  # other's independent check; the reason to skip it was the reporting, and the reporting is
  # fixed. Absent DOM captures skip informatively (L8), which is what a guard is for.
  # It never gates: severity attaches to the RECORD (claude: the API capture), and a
  # witness diverging from a complete record is drift — stated, remedied by audit's INFO,
  # never a run failure. Role-indexed, not mechanism-indexed.
  step_if "$has_dom" 'when data/input/claude/chat/browser-DOM holds captures' \
       compare_markdown      "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/compare_markdown.py" \
    --projection "$REPO_DIR/data/output/markdown/claude/chat/conversations" --dom "$browser_dom"
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
