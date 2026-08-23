#!/usr/bin/env bash
# Convert and validate Claude Code CLI session transcripts, from the STORE.
#
# The pipeline sources data/input/claude/code/machine-transport — the repo-owned, medium-carried store
# (<machine>/<project>/<session>.jsonl + <project>/memory/) — and NEVER touches
# the harness-owned ~/.claude/projects, which Anthropic expires at will.
# `corpus-yoga agent capture --all` is the capture step that populates the store
# from the live projects root; run it early and often.
#
# Usage:
#   src/main/pipeline/code-agents/run.sh --code-agent  <path>   # one project: data/input/claude/code/machine-transport/<machine>/<project>
#   src/main/pipeline/code-agents/run.sh --code-agents <path>   # the whole store: data/input/claude/code/machine-transport
#   src/main/pipeline/code-agents/run.sh --plan   # print the ordered step list; run nothing
#
# The step lists below (machine_housekeeping, run_one, run_memory, corpus) are the
# ONE authority on order: --plan prints exactly the lists that execute (see
# src/main/steps.sh).

set -euo pipefail

SELF='src/main/pipeline/code-agents/run.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
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
  # Conversion only: validation is enumerated store-wide and dispatched
  # per datum-version pair (#395), then rolled up per datum.
  local jsonl="$1" machine="$2" project_name="$3"
  local session; session="$(basename "${jsonl%.jsonl}")"
  local out_dir="$CACHE_DIR/$machine/$project_name/$session"
  step ensure_session_dir   mkdir -p "$out_dir"
  step jsonl_to_json        "$SCRIPT_DIR/jsonl_to_json.sh" "$jsonl" "$out_dir/session.json"
  step project_conversation "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/project_conversation.py" "$out_dir"
}

run_memory() {
  local project_dir="$1" machine="$2" name="$3" guard="$4"
  local out_dir="$CACHE_DIR/$machine/$name/memory"
  step_if "$guard" 'when the project has a memory/ dir' memory_to_json \
    "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/memory_to_json.py" "${project_dir%/}/memory" "$out_dir/memory.json"
}

# ── Dispatch workers (#395): one task each, machine/project derived from the
# task itself — a worker learns nothing from scope, so any worker can take any
# task. Output buffers per task; dispatch_emit restores enumeration order. ──

# One session conversion. The task is the store path
# (<store>/<machine>/<project>/<session>.jsonl); machine and project derive.
convert_one_session() {
  local jsonl="$1" project_dir machine name
  project_dir="$(dirname "$jsonl")"
  machine="$(basename "$(dirname "$project_dir")")"
  name="$(basename "$project_dir")"
  echo "$machine/$name/$(basename "${jsonl%.jsonl}")"
  run_one "$jsonl" "$machine" "$name"
}

# One memory conversion. The task is the store project dir; guard is by
# construction — only projects holding memory/ are enumerated.
convert_one_memory() {
  local project_dir="$1" machine name
  machine="$(basename "$(dirname "${project_dir%/}")")"
  name="$(basename "${project_dir%/}")"
  echo "$machine/$name/memory"
  run_memory "$project_dir" "$machine" "$name" 1
}

# One datum-version pair. The task line is validate_versions.py --pair's argv,
# tab-separated, as validate.sh --enumerate printed it. Quiet: a current log
# is a task already done (#369); the roll-up states every verdict.
validate_one_pair() {
  local input schema log_dir label
  IFS="$(printf '\t')" read -r input schema log_dir label <<TASK
$1
TASK
  step validate_pair "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
    --pair "$input" "$schema" "$log_dir" "$label"
}

# One family roll-up: the dir face of validate.sh over pair logs that are all
# current, so it relays verdicts (#363) and renders the matrix. The task is
# "session<TAB><dir>" or "memory<TAB><dir>".
rollup_one() {
  local kind dir
  IFS="$(printf '\t')" read -r kind dir <<TASK
$1
TASK
  case "$kind" in
    session) step validate        "$SCRIPT_DIR/validate.sh" --code-agent-session "$dir" ;;
    memory)  step validate_memory "$SCRIPT_DIR/validate.sh" --code-agent-memory  "$dir" ;;
  esac
}

corpus() {
  step render_corpus "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/render_corpus.py"
}

# The whole run over the given store project dirs, in four dispatched phases
# (#395): housekeeping (serial: it prunes the cache the phases fill), then
# conversions, then every datum-version pair, then the per-datum roll-ups.
# Enumeration is capacity-blind; enumeration order is listing order, and
# dispatch_emit restores it, so YOGA_JOBS=1 and =N emit identical bytes.
run_store() {
  local project_dirs=("$@")
  local project_dir machine name

  local jsonls=() memory_projects=() jsonl
  for project_dir in "${project_dirs[@]}"; do
    machine="$(basename "$(dirname "${project_dir%/}")")"
    name="$(basename "${project_dir%/}")"
    echo "$machine/$name"
    project_housekeeping "$project_dir" "$machine" "$name"
    local found=0
    for jsonl in "${project_dir%/}"/*.jsonl; do
      [[ -f "$jsonl" ]] || continue
      jsonls+=("$jsonl")
      found=1
    done
    [[ "$found" == "1" ]] || echo "  (no .jsonl files found)"
    [[ -d "${project_dir%/}/memory" ]] && memory_projects+=("${project_dir%/}")
  done

  if [[ ${#jsonls[@]} -gt 0 ]]; then
    dispatch convert_one_session "${jsonls[@]}"
    dispatch_emit
  fi
  if [[ ${#memory_projects[@]} -gt 0 ]]; then
    dispatch convert_one_memory "${memory_projects[@]}"
    dispatch_emit
  fi

  # Enumerate every datum-version pair (validate.sh owns the datum-to-family
  # mapping), then every roll-up, both in the conversions' order.
  local pairs=() rollups=() out_dir line session
  for jsonl in ${jsonls[@]+"${jsonls[@]}"}; do
    project_dir="$(dirname "$jsonl")"
    machine="$(basename "$(dirname "$project_dir")")"
    name="$(basename "$project_dir")"
    session="$(basename "${jsonl%.jsonl}")"
    out_dir="$CACHE_DIR/$machine/$name/$session"
    while IFS= read -r line; do
      pairs+=("$line")
    done < <("$SCRIPT_DIR/validate.sh" --enumerate --code-agent-session "$out_dir")
    rollups+=("$(printf 'session\t%s' "$out_dir")")
  done
  for project_dir in ${memory_projects[@]+"${memory_projects[@]}"}; do
    machine="$(basename "$(dirname "$project_dir")")"
    name="$(basename "$project_dir")"
    out_dir="$CACHE_DIR/$machine/$name/memory"
    while IFS= read -r line; do
      pairs+=("$line")
    done < <("$SCRIPT_DIR/validate.sh" --enumerate --code-agent-memory "$out_dir")
    rollups+=("$(printf 'memory\t%s' "$out_dir")")
  done

  if [[ ${#pairs[@]} -gt 0 ]]; then
    dispatch validate_one_pair "${pairs[@]}"
    dispatch_emit
  fi
  if [[ ${#rollups[@]} -gt 0 ]]; then
    dispatch rollup_one "${rollups[@]}"
    dispatch_emit
  fi
}

print_plan() {
  echo "code-agents steps — once, against the store root:"
  machine_housekeeping '<store-root>'
  echo "then per machine/project directory:"
  project_housekeeping '<project-dir>' '<machine>' '<project>'
  echo "then per session .jsonl, dispatched to the next free worker (#395):"
  run_one '<session>.jsonl' '<machine>' '<project>'
  echo "then per project with a memory/ dir, dispatched likewise:"
  run_memory '<project-dir>' '<machine>' '<project>' '0'
  echo "then per datum-version pair across the run, dispatched likewise:"
  validate_one_pair "$(printf '<input>\t<schema-file>\t<log-dir>\t<label>')"
  echo "then per datum, the family roll-up, dispatched likewise:"
  rollup_one "$(printf 'session\t<session-dir>')"
  rollup_one "$(printf 'memory\t<memory-dir>')"
  echo "then once, after all projects:"
  corpus
}

main() {
  parse_args "$@"
  if [[ "$plan" == "1" ]]; then print_plan; exit 0; fi
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ -n "$code_project" ]]; then
    local project_dir
    project_dir="$(cd "$code_project" && pwd)"
    run_store "$project_dir"
    corpus
    return 0
  fi

  if [[ ! -d "$code_projects" ]]; then
    echo "no store at $code_projects (hand-make data/input/claude/code/machine-transport as a symlink to the shared store;"
    echo "populate it via: corpus-yoga agent capture --all)"
    exit 0
  fi
  local store_root; store_root="$(cd "$code_projects" && pwd)"
  machine_housekeeping "$store_root"
  local project_dirs=() machine_dir project_dir
  for machine_dir in "$store_root"/*/; do
    [[ -d "$machine_dir" ]] || continue
    for project_dir in "${machine_dir%/}"/-Users-*/; do
      [[ -d "$project_dir" ]] || continue
      project_dirs+=("${project_dir%/}")
    done
  done
  if [[ ${#project_dirs[@]} -gt 0 ]]; then
    run_store "${project_dirs[@]}"
  fi
  corpus
}

main "$@"
