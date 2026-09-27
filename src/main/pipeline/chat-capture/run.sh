#!/usr/bin/env bash
# Validate browser-captured API JSON files against the apiConversation schema, and
# project every provider's captures - claude's API captures, gemini's DOM captures - into
# the markdown corpus.
#
# Usage:
#   src/main/pipeline/chat-capture/run.sh
#   src/main/pipeline/chat-capture/run.sh --input 'data/input/<provider>/chat/<qualifier>-capture'
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
# shellcheck source=src/main/tier.sh
source "$REPO_DIR/src/main/tier.sh"

# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"

parse_args() {
  capture_dir=""
  # The default input root is the DECLARED one: pipeline.json is the one committed
  # authority for this path — read, never restated. It is a template, <provider> and
  # <qualifier> resolved per provider by resolve_input.
  input_root="$(tier_path "$(jq -r .input "$SCRIPT_DIR/pipeline.json")")"
  plan="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --item)  capture_dir="$2";  shift 2 ;;
      --input) if [[ $# -gt 1 && "${2-}" != --* ]]; then input_root="$2"; shift 2; else shift; fi ;;
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
  local root="${1%/}" dom_root="${2%/}" store="${3%/}"
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
    "$SCRIPT_DIR/gemini/project_markdown.py" --dom-capture "$dom_root"
  # audit: capture-health report against the fresh projections — findings
  # inform, never gate: severity attaches to the RECORD, and the record was already
  # schema-validated above
  step_ok audit     "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/audit.py" \
    --input "$store" \
    --api "$DATA_DIR/output/markdown/claude/chat/conversations"
}

print_plan() {
  echo "chat-capture steps — corpus mode (default):"
  run_corpus '<captures-root>' '<scrapes-root>' '<store-root>'
  echo "single-capture mode (--item <dir>): the validate step only"
}

main() {
  parse_args "$@"
  if [[ "$plan" == "1" ]]; then print_plan; exit 0; fi
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$capture_dir" ]]; then
    run_one "$(cd "$capture_dir" && pwd)"
  else
    # Each provider's store is the template made its own; the store root above
    # <provider> is what the audit walks.
    local api_root dom_root store
    api_root="$(resolve_input "$input_root" "$SCRIPT_DIR/pipeline.json" claude)"
    dom_root="$(resolve_input "$input_root" "$SCRIPT_DIR/pipeline.json" gemini)"
    store="${input_root%%/<provider>/*}"
    if [[ ! -d "$api_root" ]]; then
      echo "no captures in $api_root (populate via: corpus-yoga browser capture --provider claude)"
      exit 0
    fi
    local root; root="$(cd "$api_root" && pwd)"
    if ! compgen -G "$root/*/" > /dev/null; then
      echo "no captures in $root"
    else
      run_corpus "$root" "$dom_root" "$store"
    fi
  fi
}

main "$@"
