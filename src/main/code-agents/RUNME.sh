#!/usr/bin/env bash
# Convert and validate Claude Code CLI session transcripts, from the STORE.
#
# The pipeline sources data/input/claude/code/machine-transport — the repo-owned, medium-carried store
# (<machine>/<project>/<session>.jsonl + <project>/memory/) — and NEVER touches
# the harness-owned ~/.claude/projects, which Anthropic expires at will.
# `yoga agent capture --all` is the capture step that populates the store
# from the live projects root; run it early and often.
#
# Usage:
#   ./src/main/code-agents/RUNME.sh --code-agent  <path>   # one project: data/input/claude/code/machine-transport/<machine>/<project>
#   ./src/main/code-agents/RUNME.sh --code-agents <path>   # the whole store: data/input/claude/code/machine-transport
#   ./src/main/code-agents/RUNME.sh --plan   # print the ordered step list; run nothing
#
# The step lists below (machine_housekeeping, run_one, run_memory, corpus) are the
# ONE authority on order: --plan prints exactly the lists that execute (see
# src/main/steps.sh).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CACHE_DIR="$REPO_DIR/tmp/cache/code-agents"

# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"

parse_args() {
  code_project=""
  code_projects=""
  plan="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --code-agent)  code_project="$2";  shift 2 ;;
      --code-agents) code_projects="$2"; shift 2 ;;
      --plan)          plan="1";           shift   ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --code-agent <path> | --code-agents <path> | --plan"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ "$plan" == "0" && -z "$code_project" && -z "$code_projects" ]]; then
    echo "Usage: $0 --code-agent <path/to/machine/project-directory>"
    echo "       $0 --code-agents <path/to/store-root>"
    echo
    echo "  project-directory: a machine's project under the store, e.g.:"
    echo "    data/input/claude/code/machine-transport/<machine>/\$(pwd | tr '/' '-')"
    echo "Pass --help for more information."
    exit 1
  fi
}

prune_departed() {
  # No blanket wipe: the validation logs under tmp/cache/ ARE the memoisation (an
  # unchanged session revalidates against nothing), and jsonl_to_json keeps
  # session.json's mtime when content is unchanged for the same reason. cache
  # derivations die with their STORE datum — and the store is repo-owned, so
  # a departure there was a deliberate disposal, never harness expiry.
  local project_dir="$1" machine="$2" name="$3"
  for existing in "$CACHE_DIR/$machine/$name"/*/; do
    [[ -d "$existing" ]] || continue
    local sess; sess="$(basename "${existing%/}")"
    if [[ "$sess" == "memory" ]]; then
      [[ -d "${project_dir%/}/memory" ]] || rm -rf "${existing:?}"
      continue
    fi
    [[ -f "${project_dir%/}/$sess.jsonl" ]] || rm -rf "${existing:?}"
  done
}

prune_departed_projects() {
  # A cache project dir whose store project is gone dies whole; a top-level cache
  # dir that is not a machine in the store (the pre-store flat layout, or a
  # removed machine) dies too — every cache path mirrors a store path or goes.
  local store_root="$1"
  for machine_dir in "$CACHE_DIR"/*/; do
    [[ -d "$machine_dir" ]] || continue
    local machine; machine="$(basename "${machine_dir%/}")"
    if [[ ! -d "${store_root%/}/$machine" ]]; then
      rm -rf "${machine_dir:?}"
      continue
    fi
    for proj_dir in "$machine_dir"*/; do
      [[ -d "$proj_dir" ]] || continue
      local proj; proj="$(basename "${proj_dir%/}")"
      [[ -d "${store_root%/}/$machine/$proj" ]] || rm -rf "${proj_dir:?}"
    done
  done
}

machine_housekeeping() {
  step prune_departed_gen prune_departed_projects "$1"
}

project_housekeeping() {
  step prune_departed_sessions prune_departed "$1" "$2" "$3"
}

run_one() {
  local jsonl="$1" machine="$2" project_name="$3"
  local session; session="$(basename "${jsonl%.jsonl}")"
  local out_dir="$CACHE_DIR/$machine/$project_name/$session"
  step ensure_session_dir   mkdir -p "$out_dir"
  step jsonl_to_json        "$SCRIPT_DIR/jsonl_to_json.sh" "$jsonl" "$out_dir/session.json"
  step project_conversation "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/project_conversation.py" "$out_dir"
  step validate             "$SCRIPT_DIR/validate.sh" --code-agent-session "$out_dir"
}

run_memory() {
  local project_dir="$1" machine="$2" name="$3" guard="$4"
  local out_dir="$CACHE_DIR/$machine/$name/memory"
  step_if "$guard" 'when the project has a memory/ dir' memory_to_json \
    "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/memory_to_json.py" "${project_dir%/}/memory" "$out_dir/memory.json"
  step_if "$guard" 'when the project has a memory/ dir' validate_memory \
    "$SCRIPT_DIR/validate.sh" --code-agent-memory "$out_dir"
}

corpus() {
  step render_corpus "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/render_corpus.py"
}

run_project() {
  local project_dir="$1" machine="$2"
  local name; name="$(basename "${project_dir%/}")"
  echo "$machine/$name"
  project_housekeeping "$project_dir" "$machine" "$name"
  local found=0
  for jsonl in "${project_dir%/}"/*.jsonl; do
    [[ -f "$jsonl" ]] || continue
    found=1
    run_one "$jsonl" "$machine" "$name"
  done
  [[ "$found" -eq 1 ]] || echo "  (no .jsonl files found)"
  local has_memory=0
  [[ -d "${project_dir%/}/memory" ]] && has_memory=1
  run_memory "$project_dir" "$machine" "$name" "$has_memory"
}

print_plan() {
  echo "code-agents steps — once, against the store root:"
  machine_housekeeping '<store-root>'
  echo "then per machine/project directory:"
  project_housekeeping '<project-dir>' '<machine>' '<project>'
  echo "then per session .jsonl within it:"
  run_one '<session>.jsonl' '<machine>' '<project>'
  echo "then per project:"
  run_memory '<project-dir>' '<machine>' '<project>' '0'
  echo "then once, after all projects:"
  corpus
}

main() {
  parse_args "$@"
  if [[ "$plan" == "1" ]]; then print_plan; exit 0; fi
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$code_project" ]]; then
    local project_dir machine
    project_dir="$(cd "$code_project" && pwd)"
    machine="$(basename "$(dirname "$project_dir")")"
    run_project "$project_dir" "$machine"
    corpus
    return 0
  fi

  if [[ ! -d "$code_projects" ]]; then
    echo "no store at $code_projects (hand-make data/input/claude/code/machine-transport as a symlink to the shared store;"
    echo "populate it via: ./yoga agent capture --all)"
    exit 0
  fi
  local store_root; store_root="$(cd "$code_projects" && pwd)"
  machine_housekeeping "$store_root"
  for machine_dir in "$store_root"/*/; do
    [[ -d "$machine_dir" ]] || continue
    local machine; machine="$(basename "${machine_dir%/}")"
    for project_dir in "${machine_dir%/}"/-Users-*/; do
      [[ -d "$project_dir" ]] || continue
      run_project "${project_dir%/}" "$machine"
    done
  done
  corpus
}

main "$@"
