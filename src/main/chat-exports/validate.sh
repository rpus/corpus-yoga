#!/usr/bin/env bash
# Validate a single chat export against the conversations schema.
#
# Usage:
#   src/main/chat-exports/validate.sh --chat-export <path/to/data-directory>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMA_DIR="$REPO_DIR/rsc/schema/chat-exports"
CACHE_DIR="$REPO_DIR/cache/chat-exports"

rel_path() {
  "$REPO_DIR/src/run_python_script.sh" -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$1" "$REPO_DIR"
}

file_info() {
  local f="$1"
  local lines bytes
  lines="$(wc -l < "$f" | xargs)"
  bytes="$(wc -c < "$f" | xargs)"
  echo "$f: $lines lines, $bytes bytes"
}

on_failure() {
  local f="$1" schema="$2" python_out="$3"
  local path_raw path_json instance_ptr schema_ptr jq_filter
  path_raw="$(echo "$python_out" | grep "^Path:" | sed 's/^Path: //')" || true
  [[ -z "$path_raw" ]] && return
  path_json="$(echo "$path_raw" | tr "'" '"')"
  echo "--- jq inspection ---"
  jq "getpath($path_json)" "$f"
  instance_ptr="$("$REPO_DIR/src/run_python_script.sh" -c "import ast,sys; p=ast.literal_eval(sys.argv[1]); print('/'+'/'.join(str(x) for x in p))" "$path_raw")"
  schema_ptr="$("$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/schema_path.py" "$path_raw" "$schema")"
  echo "--- instance path ---"
  echo "$(rel_path "$f")#${instance_ptr}"
  echo "--- schema path ---"
  echo "$(rel_path "$schema")${schema_ptr}"
  echo "--- schema fragment ---"
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/schema_fragment.py" "$schema_ptr" "$schema"
  echo "--- schema occurrences ---"
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/schema_occurrences.py" "$schema_ptr" "$schema" "$f" | sed 's/^/  /'
  # shellcheck disable=SC2016  # $p is a jq variable, not a shell expansion
  jq_filter='[inputs as $p | {key: ($p|tostring), value: ($inst[0]|getpath($p))}] | from_entries'
  echo "--- fetch occurrences command ---"
  echo "src/run_python_script.sh \"$(rel_path "$REPO_DIR/src/main/schema_occurrences.py")\" \"$schema_ptr\" \"$(rel_path "$schema")\" \"$(rel_path "$f")\" \\"
  echo "  | jq -n --slurpfile inst \"$(rel_path "$f")\" \\"
  echo "    '$jq_filter'"
}

# True iff the existing log demonstrably describes the current datum × schema: it
# postdates both files and its recorded byte sizes match. Lets an unchanged pair skip
# revalidation — the log IS the memoisation. (Same contract as validate_versions.py.)
log_current() {
  local out="$1" f="$2" schema="$3"
  [[ -f "$out" && "$out" -nt "$f" && "$out" -nt "$schema" ]] || return 1
  local fb sb
  fb="$(wc -c < "$f" | xargs)"
  sb="$(wc -c < "$schema" | xargs)"
  sed -n '2p' "$out" | grep -q ", ${fb} bytes$" && sed -n '3p' "$out" | grep -q ", ${sb} bytes$"
}

validate_file() {
  local f="$1" schema="$2" out="$3"
  if log_current "$out" "$f" "$schema"; then
    skipped=$((skipped + 1))
    return
  fi
  {
    date -Iseconds
    file_info "$f"
    file_info "$schema"
    local python_out
    python_out="$("$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/validate.py" "$f" "$schema")"
    echo "$python_out"
    if ! echo "$python_out" | grep -qx "Valid!"; then
      on_failure "$f" "$schema" "$python_out"
    fi
  } > "$out"
  validated=$((validated + 1))
}

validate_export() {
  local chat_export="${1%/}"
  local validation_dir
  validation_dir="$CACHE_DIR/$(basename "$chat_export")/validation"

  skipped=0
  validated=0
  mkdir -p "$validation_dir"

  for f in "$chat_export"/*.json; do
    local name schemas schema schema_stem
    name="$(basename "${f%.json}")"
    if [[ -d "$SCHEMA_DIR/$name" ]]; then
      schemas=()
      while IFS= read -r s; do schemas+=("$s"); done < <(find "$SCHEMA_DIR/$name" -name "*.json" -type f)
    else
      schemas=("$SCHEMA_DIR/${name}.json")
    fi
    for schema in "${schemas[@]}"; do
      [[ -e "$schema" ]] || continue
      schema_stem="${schema#"$SCHEMA_DIR/"}"
      schema_stem="${schema_stem%.json}"
      mkdir -p "$validation_dir/$(dirname "$schema_stem")"
      validate_file "$f" "$schema" "$validation_dir/${schema_stem}.log"
    done
  done

  for d in "$chat_export"/*/; do
    [[ -d "$d" ]] || continue
    local dname
    dname="$(basename "$d")"
    [[ -d "$SCHEMA_DIR/$dname" ]] || continue
    for f in "$d"*.json; do
      [[ -f "$f" ]] || continue
      local item_name schemas schema schema_stem
      item_name="$(basename "${f%.json}")"
      schemas=()
      while IFS= read -r s; do schemas+=("$s"); done < <(find "$SCHEMA_DIR/$dname" -name "*.json" -type f)
      for schema in "${schemas[@]}"; do
        schema_stem="${schema#"$SCHEMA_DIR/"}"
        schema_stem="${schema_stem%.json}"
        mkdir -p "$validation_dir/${dname}/${item_name}"
        validate_file "$f" "$schema" "$validation_dir/${dname}/${item_name}/$(basename "$schema_stem").log"
      done
    done
  done

  # A component modelled by NO version is a schema-frontier event and must say
  # FAIL: — the tail hoists that sigil. validate_versions.py already shouts for
  # the capture pipelines; this wrapper's roll-up must not stay quiet (the
  # 2026-07 batch failed every conversations version and the tail showed
  # nothing until the next pre_commit).
  local family fam_dir
  for fam_dir in "$SCHEMA_DIR"/*/; do
    [[ -d "$fam_dir" ]] || continue
    family="$(basename "${fam_dir%/}")"
    local logs=("$validation_dir/$family"/v*.log)
    [[ -e "${logs[0]}" ]] || continue
    if ! grep -qx "Valid!" "${logs[@]}" 2>/dev/null; then
      echo "  FAIL: $(basename "$chat_export"): ${family} NOT modelled by any of the ${#logs[@]} version(s) validated — follow rsc/schema/WORKFLOW.md"
    fi
  done

  echo "  validated ${validated}, current (skipped) ${skipped}"

  # Validation owns the datum's machine-local matrix: render matrix.md from the logs
  # just written (see rsc/schema/WORKFLOW.md).
  "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/validation_matrix.py" \
    "$(dirname "$validation_dir")" "$SCHEMA_DIR"
}

parse_args() {
  chat_export=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --chat-export) chat_export="$2"; shift 2 ;;
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
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
