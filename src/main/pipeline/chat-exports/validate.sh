#!/usr/bin/env bash
# Validate a single chat export: every component and piece against its whole
# schema family, through the one single-pair face (#396).
#
# This file only ENUMERATES: datum-version pairs dispatched to
# validate_versions.py --pair (#395), then one family roll-up per datum (the
# directory face: verdict lines from the current pair logs, and the export's
# matrix.md). Component and piece differ only in where the schema family and
# the log directory derive from.
#
# Usage:
#   src/main/pipeline/chat-exports/validate.sh --chat-export <path/to/data-directory>

set -euo pipefail

SELF='src/main/pipeline/chat-exports/validate.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
SCHEMA_DIR="$REPO_DIR/rsc/schema/chat-exports"
CACHE_DIR="$REPO_DIR/tmp/cache/chat-exports"

# shellcheck source=src/main/steps.sh
source "$REPO_DIR/src/main/steps.sh"   # dispatch/dispatch_emit — next-free dispatch (#395)

# One datum-version pair: the task line is validate_versions.py --pair's argv,
# tab-separated. Quiet — a current log is a task already done (#369).
validate_one_pair() {
  local input schema log_dir label
  IFS="$(printf '\t')" read -r input schema log_dir label <<TASK
$1
TASK
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
    --pair "$input" "$schema" "$log_dir" "$label"
}

# One family roll-up: the directory face over pair logs that are all current,
# so it relays verdicts (#363) and renders the export's matrix. SERIAL: every
# roll-up of one export rewrites the same matrix.md, so they must not race.
rollup_one() {
  local input family log_dir label
  IFS="$(printf '\t')" read -r input family log_dir label <<TASK
$1
TASK
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate_versions.py" \
    "$input" "$family" "$log_dir" "$label"
}

validate_export() {
  local chat_export="${1%/}"
  local validation_dir
  validation_dir="$CACHE_DIR/$(basename "$chat_export")/validation"
  mkdir -p "$validation_dir"

  # Enumerate, capacity-blind (#395): components at the export root, pieces one
  # directory down, each against every version of its family. A datum whose
  # name matches no schema family is not this pipeline's subject.
  local pairs=() rollups=() f name d dname item schema log_dir label
  for f in "$chat_export"/*.json; do
    [[ -f "$f" ]] || continue
    name="$(basename "${f%.json}")"
    [[ -d "$SCHEMA_DIR/$name" ]] || continue
    log_dir="$validation_dir/$name"
    for schema in "$SCHEMA_DIR/$name"/v*.json; do
      [[ -e "$schema" ]] || continue
      pairs+=("$(printf '%s\t%s\t%s\t%s' "$f" "$schema" "$log_dir" "$name")")
    done
    rollups+=("$(printf '%s\t%s\t%s\t%s' "$f" "$SCHEMA_DIR/$name" "$log_dir" "$name")")
  done
  for d in "$chat_export"/*/; do
    [[ -d "$d" ]] || continue
    dname="$(basename "${d%/}")"
    [[ -d "$SCHEMA_DIR/$dname" ]] || continue
    for f in "$d"*.json; do
      [[ -f "$f" ]] || continue
      item="$(basename "${f%.json}")"
      log_dir="$validation_dir/$dname/$item"
      label="$dname/$item"
      for schema in "$SCHEMA_DIR/$dname"/v*.json; do
        [[ -e "$schema" ]] || continue
        pairs+=("$(printf '%s\t%s\t%s\t%s' "$f" "$schema" "$log_dir" "$label")")
      done
      rollups+=("$(printf '%s\t%s\t%s\t%s' "$f" "$SCHEMA_DIR/$dname" "$log_dir" "$label")")
    done
  done

  if [[ ${#pairs[@]} -gt 0 ]]; then
    dispatch validate_one_pair "${pairs[@]}"
    dispatch_emit
  fi
  local rollup
  for rollup in ${rollups[@]+"${rollups[@]}"}; do
    rollup_one "$rollup"
  done
}

parse_args() {
  chat_export=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export) chat_export="$2"; shift 2 ;;
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *)
        echo "Unknown argument: $1"
        echo "Usage: $0 --chat-export <path>"
        echo "Pass --help for more information."; exit 1 ;;
    esac
  done
  if [[ -z "$chat_export" ]]; then
    echo "Usage: $0 --chat-export <path/to/data-directory>"
    echo "Pass --help for more information."
    exit 1
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  validate_export "$(cd "$chat_export" && pwd)"
}

main "$@"
