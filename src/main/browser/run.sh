#!/usr/bin/env bash
# Validate and render every provider's browser captures - claude's API captures, gemini's DOM
# captures - each on its own; with --collate, place the renderings in the markdown corpus, whose
# names are each conversation's place among them all.
#
# Usage:
#   src/main/browser/run.sh
#   src/main/browser/run.sh --input 'data/input/<provider>/chat/<qualifier>-capture'
#   src/main/browser/run.sh --item  data/input/claude/chat/API-capture/<uuid>
#   src/main/browser/run.sh --collate [--input <root>]
#   src/main/browser/run.sh --plan   # print the ordered step list; run nothing
#
# The step lists below (run_corpus, collate_corpus) are the ONE authority on order: --plan
# prints exactly the lists that execute (see src/main/steps.sh).

set -euo pipefail

SELF='src/main/browser/run.sh'
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
  collate="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --item)  capture_dir="$2";  shift 2 ;;
      --input) if [[ $# -gt 1 && "${2-}" != --* ]]; then input_root="$2"; shift 2; else shift; fi ;;
      --plan)             plan="1"; shift ;;
      --collate)          collate="1"; shift ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 [--input <path>] [--collate] | --item <path> | --plan"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

run_one() {
  local input_dir="${1%/}"
  map step validate "$SCRIPT_DIR/claude/validate.sh" --capture "$input_dir"
  map step render "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/claude/render.py" --capture "$input_dir"
}

# each provider's steps run where that provider's captures stand (issues/965): a room
# holding gemini's alone, or claude's alone, runs the one and skips the other
held() {
  has_api=0 has_dom=0
  [[ -n "$1" ]] && compgen -G "$1/*/" > /dev/null && has_api=1
  [[ -d "$2" ]] && has_dom=1
  return 0
}

run_corpus() {
  local root="${1%/}" dom_root="${2%/}" has_api has_dom
  held "$root" "$dom_root"
  # validate: announces itself once and folds the all-current captures into one
  # summary line, so a 95-capture steady state is one line
  map step_if "$has_api" "where claude's API captures stand" validate "$SCRIPT_DIR/claude/validate.sh" --api-capture "$root"
  # gemini: each scrape lifted and judged against the markdownConversation family
  map step_if "$has_dom" "where gemini's DOM captures stand" validate_gemini "$SCRIPT_DIR/gemini/validate.sh" --dom-capture "$dom_root"
  # render: each conversation's markdown at its own cache address, which the collate names
  # and places (issues/1195)
  map step_if "$has_api" "where claude's API captures stand" render "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/claude/render.py" --api-capture "$root"
  map step_if "$has_dom" "where gemini's DOM captures stand" render_gemini "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/gemini/render.py" --dom-capture "$dom_root"
}

collate_corpus() {
  local root="${1%/}" dom_root="${2%/}" has_api has_dom
  held "$root" "$dom_root"
  # current: nothing is placed older than its input - every unit's run output was made from
  # the input as it stands, or the collate stops here, naming what the run is owed (issues/1183)
  reduce step current "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validation_audit.py" --owed browser
  # project_markdown: the run's renderings, each named for its place among them all and
  # dressed with what the whole corpus says of it
  reduce step_if "$has_api" "where claude's API captures stand" project_markdown "$REPO_DIR/src/run_python_script.sh" \
    "$REPO_DIR/src/main/project_markdown.py" --api-capture "$root"
  # gemini: each rendered scrape placed in the presentation tree beside claude's projections
  # (data/output/markdown/{claude,gemini}); a slug collision gets the conversation id prefixed.
  reduce step_if "$has_dom" "where gemini's DOM captures stand" gemini_project_markdown "$REPO_DIR/src/run_python_script.sh" \
    "$SCRIPT_DIR/gemini/project_markdown.py" --dom-capture "$dom_root"
  # audit: capture-health report against the fresh projections — findings
  # inform, never gate: severity attaches to the RECORD, and the record was already
  # schema-validated by the run
  # record: what this collate read, so the status offers the next only once the run's output moves (issues/1188)
  reduce step record "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validation_audit.py" --collated browser
  reduce step_ok audit     "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/audit.py"
}

print_plan() {
  if [[ "$collate" == "1" ]]; then
    echo "browser steps — collate mode (--collate):"
    collate_corpus '<captures-root>' '<scrapes-root>'
    return
  fi
  echo "browser steps — corpus mode (default):"
  run_corpus '<captures-root>' '<scrapes-root>'
  echo "single-capture mode (--item <dir>): the validate and render steps only"
}

main() {
  parse_args "$@"
  if [[ "$plan" == "1" ]]; then print_plan; exit 0; fi
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$capture_dir" ]]; then
    run_one "$(cd "$capture_dir" && pwd)"
  else
    # Each provider's store is the template made its own.
    local api_root dom_root
    api_root="$(resolve_input "$input_root" "$SCRIPT_DIR/pipeline.json" claude)"
    dom_root="$(resolve_input "$input_root" "$SCRIPT_DIR/pipeline.json" gemini)"
    local root=''
    if [[ -d "$api_root" ]]; then
      root="$(cd "$api_root" && pwd)"
      compgen -G "$root/*/" > /dev/null || echo "no captures in $root"
    else
      echo "no captures in $api_root (populate via: corpus-yoga browser capture --provider claude)"
    fi
    if [[ "$collate" == "1" ]]; then
      collate_corpus "$root" "$dom_root"
    else
      run_corpus "$root" "$dom_root"
    fi
  fi
}

main "$@"
