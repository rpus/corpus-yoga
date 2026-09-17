#!/usr/bin/env bash
# Validate browser-captured API JSON files against the apiConversation schema.
#
# Usage:
#   src/main/pipeline/chat-capture/run.sh
#   src/main/pipeline/chat-capture/run.sh --input data/input/claude/chat/API-capture
#   src/main/pipeline/chat-capture/run.sh --item  data/input/claude/chat/API-capture/<uuid>
#   src/main/pipeline/chat-capture/run.sh --plan   # print the ordered step list; run nothing
#
# The step list below (run_corpus) is the ONE authority on order: --plan prints
# exactly the list that executes (see src/main/steps.sh).

set -euo pipefail

SELF='src/main/pipeline/chat-capture/run.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"

parse_args() {
  capture_dir=""
  # The default input root is the DECLARED one: pipeline.json is the one committed
  # authority for this path — read, never restated.
  api_capture="$REPO_DIR/$(jq -r .input "$SCRIPT_DIR/pipeline.json")"
  plan="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --item)  capture_dir="$2";  shift 2 ;;
      --input) if [[ $# -gt 1 && "${2-}" != --* ]]; then api_capture="$2"; shift 2; else shift; fi ;;
      --plan)             plan="1"; shift ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 [--input <path>] | --item <path> | --plan"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

run_one() {
  local input_dir="${1%/}"
  step validate "$SCRIPT_DIR/claude/validate.sh" --capture "$input_dir"
}

run_corpus() {
  local root="${1%/}"
  # validate: announces itself once and folds the all-current captures into one
  # summary line, so a 95-capture steady state is one line
  step validate              "$SCRIPT_DIR/claude/validate.sh" --api-capture "$root"
  # project_markdown: render api JSON -> markdown always (no DOM scrape needed)
  step project_markdown      "$REPO_DIR/src/run_python_script.sh" \
    "$REPO_DIR/src/main/model/project_markdown.py" --api-capture "$root"
  # gemini/project_markdown: gemini's scrapes ARE markdown already — copy them into the
  # presentation tree beside claude's projections (data/output/markdown/{claude,gemini}),
  # anchoring each turn heading; a slug collision gets the conversation id prefixed.
  step gemini_project_markdown  "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/gemini/project_markdown.py"
  # audit: capture-health report against the fresh projections — findings
  # inform, never gate: severity attaches to the RECORD, and the record was already
  # schema-validated above
  step_ok audit     "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/audit.py" \
    --input "$REPO_DIR/data/input" \
    --api "$REPO_DIR/data/output/markdown/claude/chat/conversations"
}

print_plan() {
  echo "chat-capture steps — corpus mode (default):"
  run_corpus '<captures-root>'
  echo "single-capture mode (--item <dir>): the validate step only"
}

main() {
  parse_args "$@"
  if [[ "$plan" == "1" ]]; then print_plan; exit 0; fi
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$capture_dir" ]]; then
    run_one "$(cd "$capture_dir" && pwd)"
  else
    if [[ ! -d "$api_capture" ]]; then
      echo "no captures in $api_capture (populate via: corpus-yoga browser capture)"
      exit 0
    fi
    local root; root="$(cd "$api_capture" && pwd)"
    if ! compgen -G "$root/*/" > /dev/null; then
      echo "no captures in $root"
    else
      run_corpus "$root"
    fi
  fi
}

main "$@"
