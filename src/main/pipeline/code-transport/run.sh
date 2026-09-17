#!/usr/bin/env bash
# Convert and validate code session transcripts, from each provider's STORE.
#
# The pipeline sources data/input/<provider>/code/machine-transport — the repo-owned,
# medium-carried stores (<machine>/<project>/<session>) — for every provider that has a
# mechanism directory beside this script and a row in rsc/provider/providers.csv (#635),
# and NEVER touches a harness-owned live store, which its provider expires at will.
# `corpus-yoga agent capture --all` is the capture step that populates the stores; run it
# early and often. A provider's mechanism is three files under <provider>/:
# list_sessions.sh, session_to_json.sh and project_conversation.py, and
# memory_to_json.py where its projects carry a memory/ directory.
#
# Usage:
#   src/main/pipeline/code-transport/run.sh --item  <path>   # one project: data/input/<provider>/code/machine-transport/<machine>/<project>
#   src/main/pipeline/code-transport/run.sh --input <path>   # the stores: data/input/<provider>/code/machine-transport, <provider> literal or named
#   src/main/pipeline/code-transport/run.sh --plan   # print the ordered step list; run nothing
#
# The step lists below (machine_housekeeping, run_one, run_memory, corpus) are the
# ONE authority on order: --plan prints exactly the lists that execute (see
# src/main/steps.sh).

set -euo pipefail

SELF='src/main/pipeline/code-transport/run.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
CACHE_DIR="$REPO_DIR/tmp/cache/code-transport"

# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"

parse_args() {
  code_project=""
  code_projects=""
  plan="0"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --item)  code_project="$2";  shift 2 ;;
      --input) code_projects="$2"; shift 2 ;;
      --plan)          plan="1";           shift   ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --item <path> | --input <path> | --plan"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ "$plan" == "0" && -z "$code_project" && -z "$code_projects" ]]; then
    echo "Usage: $0 --item <path/to/machine/project-directory>"
    echo "       $0 --input <path/to/store-root>"
    echo
    echo "  project-directory: a machine's project under the store, e.g.:"
    echo "    data/input/<provider>/code/machine-transport/<machine>/\$(pwd | tr '/' '-')"
    echo "Pass --help for more information."
    exit 1
  fi
}

# The providers this pipeline serves: a mechanism directory here AND a row of the registry.
# The registry is the venv python's to read (#478); the pipeline runs after the mint.
providers() {
  local declared p
  declared="$("$REPO_DIR/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import provider; print("\n".join(provider.provider_names()))' "$REPO_DIR/src/main")"
  for p in $declared; do
    [[ -x "$SCRIPT_DIR/$p/list_sessions.sh" ]] && echo "$p"
  done
  return 0
}

# The provider a store path belongs to: the segment under data/input.
provider_of() {
  local rest="${1#*"/data/input/"}"
  echo "${rest%%/*}"
}

prune_departed() {
  # No blanket wipe: the validation logs under tmp/cache/ ARE the memoisation (an
  # unchanged session revalidates against nothing), and jsonl_to_json keeps
  # session.json's mtime when content is unchanged for the same reason. cache
  # derivations die with their STORE datum — and the store is repo-owned, so
  # a departure there was a deliberate disposal, never harness expiry.
  local project_dir="$1" machine="$2" name="$3" provider="$4" held source
  held="$("$SCRIPT_DIR/$provider/list_sessions.sh" "$project_dir" 2>/dev/null | while IFS= read -r source; do basename "${source%.jsonl}"; done)"
  for existing in "$CACHE_DIR/$provider/$machine/$name"/*/; do
    [[ -d "$existing" ]] || continue
    local sess; sess="$(basename "${existing%/}")"
    if [[ "$sess" == "memory" ]]; then
      [[ -d "${project_dir%/}/memory" ]] || rm -rf "${existing:?}"
      continue
    fi
    grep -qx -- "$sess" <<< "$held" || rm -rf "${existing:?}"
  done
}

prune_departed_projects() {
  # A cache project dir whose store project is gone dies whole; a cache dir under the
  # provider that is not a machine in its store (a removed machine) dies too — every
  # cache path mirrors a store path or goes.
  local store_root="$1" provider="$2"
  for machine_dir in "$CACHE_DIR/$provider"/*/; do
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
  step prune_departed_gen prune_departed_projects "$1" "$2"
}

project_housekeeping() {
  step prune_departed_sessions prune_departed "$1" "$2" "$3" "$4"
}

run_one() {
  # Conversion only: validation is enumerated store-wide and dispatched
  # per datum-version pair (#395), then rolled up per datum.
  local source="$1" machine="$2" project_name="$3" provider="$4"
  local session; session="$(basename "${source%.jsonl}")"
  local out_dir="$CACHE_DIR/$provider/$machine/$project_name/$session"
  step ensure_session_dir   mkdir -p "$out_dir"
  step session_to_json      "$SCRIPT_DIR/$provider/session_to_json.sh" "$source" "$out_dir/session.json" || return 1
  step project_conversation "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/$provider/project_conversation.py" "$out_dir"
}

run_memory() {
  local project_dir="$1" machine="$2" name="$3" guard="$4" provider="$5"
  local out_dir="$CACHE_DIR/$provider/$machine/$name/memory"
  step_if "$guard" 'when the project has a memory/ dir' memory_to_json \
    "$REPO_DIR/src/run_python_script.sh" "$SCRIPT_DIR/$provider/memory_to_json.py" "${project_dir%/}/memory" "$out_dir/memory.json"
}

# ── Dispatch workers (#395): one task each, machine/project derived from the
# task itself — a worker learns nothing from scope, so any worker can take any
# task. Output buffers per task; dispatch_emit restores enumeration order. ──

# One session conversion. The task is the session's store path
# (<store>/<machine>/<project>/<session>, a file or a directory as its provider
# writes one); provider, machine and project derive.
convert_one_session() {
  local source="$1" project_dir machine name provider
  project_dir="$(dirname "$source")"
  machine="$(basename "$(dirname "$project_dir")")"
  name="$(basename "$project_dir")"
  provider="$(provider_of "$source")"
  echo "$provider/$machine/$name/$(basename "${source%.jsonl}")"
  run_one "$source" "$machine" "$name" "$provider"
}

# One memory conversion. The task is the store project dir; guard is by
# construction — only projects holding memory/ are enumerated.
convert_one_memory() {
  local project_dir="$1" machine name provider
  machine="$(basename "$(dirname "${project_dir%/}")")"
  name="$(basename "${project_dir%/}")"
  provider="$(provider_of "$project_dir")"
  echo "$provider/$machine/$name/memory"
  run_memory "$project_dir" "$machine" "$name" 1 "$provider"
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
# "session<TAB><provider><TAB><dir>" or "memory<TAB><provider><TAB><dir>".
rollup_one() {
  local kind provider dir
  IFS="$(printf '\t')" read -r kind provider dir <<TASK
$1
TASK
  case "$kind" in
    session) step validate        "$SCRIPT_DIR/validate.sh" --provider "$provider" --session "$dir" ;;
    memory)  step validate_memory "$SCRIPT_DIR/validate.sh" --provider "$provider" --memory  "$dir" ;;
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
  local project_dir machine name provider

  local jsonls=() memory_projects=() jsonl
  for project_dir in "${project_dirs[@]}"; do
    machine="$(basename "$(dirname "${project_dir%/}")")"
    name="$(basename "${project_dir%/}")"
    provider="$(provider_of "$project_dir")"
    echo "$provider/$machine/$name"
    project_housekeeping "$project_dir" "$machine" "$name" "$provider"
    local found=0
    while IFS= read -r jsonl; do
      [[ -n "$jsonl" ]] || continue
      jsonls+=("$jsonl")
      found=1
    done < <("$SCRIPT_DIR/$provider/list_sessions.sh" "$project_dir")
    [[ "$found" == "1" ]] || echo "  (no sessions found)"
    [[ -d "${project_dir%/}/memory" && -f "$SCRIPT_DIR/$provider/memory_to_json.py" ]] && memory_projects+=("${project_dir%/}")
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
    provider="$(provider_of "$jsonl")"
    out_dir="$CACHE_DIR/$provider/$machine/$name/$session"
    while IFS= read -r line; do
      pairs+=("$line")
    done < <("$SCRIPT_DIR/validate.sh" --enumerate --provider "$provider" --session "$out_dir")
    rollups+=("$(printf 'session\t%s\t%s' "$provider" "$out_dir")")
  done
  for project_dir in ${memory_projects[@]+"${memory_projects[@]}"}; do
    machine="$(basename "$(dirname "$project_dir")")"
    name="$(basename "$project_dir")"
    provider="$(provider_of "$project_dir")"
    out_dir="$CACHE_DIR/$provider/$machine/$name/memory"
    while IFS= read -r line; do
      pairs+=("$line")
    done < <("$SCRIPT_DIR/validate.sh" --enumerate --provider "$provider" --memory "$out_dir")
    rollups+=("$(printf 'memory\t%s\t%s' "$provider" "$out_dir")")
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
  local provider mechanism
  echo "code-transport steps — once per provider, against its store root:"
  machine_housekeeping '<store-root>' '<provider>'
  echo "then per machine/project directory:"
  project_housekeeping '<project-dir>' '<machine>' '<project>' '<provider>'
  for mechanism in "$SCRIPT_DIR"/*/list_sessions.sh; do
    provider="$(basename "$(dirname "$mechanism")")"
    echo "then per $provider session, dispatched to the next free worker (#395):"
    run_one '<session>' '<machine>' '<project>' "$provider"
    [[ -f "$SCRIPT_DIR/$provider/memory_to_json.py" ]] || continue
    echo "then per $provider project with a memory/ dir, dispatched likewise:"
    run_memory '<project-dir>' '<machine>' '<project>' '0' "$provider"
  done
  echo "then per datum-version pair across the run, dispatched likewise:"
  validate_one_pair "$(printf '<input>\t<schema-file>\t<log-dir>\t<label>')"
  echo "then per datum, the family roll-up, dispatched likewise:"
  rollup_one "$(printf 'session\t<provider>\t<session-dir>')"
  rollup_one "$(printf 'memory\t<provider>\t<memory-dir>')"
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

  # Every served provider's store: <provider> in the path is each provider in turn, and
  # a path naming one provider is that provider's alone.
  local project_dirs=() machine_dir project_dir provider store store_root stores=0
  for provider in $(providers); do
    store="${code_projects//<provider>/$provider}"
    [[ "$(provider_of "$store")" == "$provider" ]] || continue
    if [[ ! -d "$store" ]]; then
      echo "no store at ${store#"$REPO_DIR/"} — will skip (populate it via: corpus-yoga agent capture --provider $provider)"
      continue
    fi
    stores=$((stores + 1))
    store_root="$(cd "$store" && pwd)"
    machine_housekeeping "$store_root" "$provider"
    for machine_dir in "$store_root"/*/; do
      [[ -d "$machine_dir" ]] || continue
      for project_dir in "${machine_dir%/}"/*/; do
        [[ -d "$project_dir" ]] || continue
        project_dirs+=("${project_dir%/}")
      done
    done
  done
  if [[ "$stores" == "0" ]]; then exit 0; fi
  if [[ ${#project_dirs[@]} -gt 0 ]]; then
    run_store "${project_dirs[@]}"
  fi
  corpus
}

main "$@"
