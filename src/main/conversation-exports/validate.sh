#!/usr/bin/env bash
# Run from the repo root, e.g.:
# src/main/conversation-exports/validate.sh --conversation-export ../conversation-exports/data-2026-04-07-07-52-05-batch-0000
# src/main/conversation-exports/validate.sh --conversation-exports ../conversation-exports

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMA_DIR="$REPO_DIR/rsc/schema"
OUTPUT_DIR="$REPO_DIR/gen/conversation-exports"

rel_path() {
  python -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$1" "$REPO_DIR"
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
  instance_ptr="$(python -c "import ast,sys; p=ast.literal_eval(sys.argv[1]); print('/'+'/'.join(str(x) for x in p))" "$path_raw")"
  schema_ptr="$(python "$SCRIPT_DIR/schema_path.py" "$path_raw" "$schema")"
  echo "--- instance path ---"
  echo "$(rel_path "$f")#${instance_ptr}"
  echo "--- schema path ---"
  echo "$(rel_path "$schema")${schema_ptr}"
  echo "--- schema fragment ---"
  python "$SCRIPT_DIR/schema_fragment.py" "$schema_ptr" "$schema"
  echo "--- schema occurrences ---"
  python "$SCRIPT_DIR/schema_occurrences.py" "$schema_ptr" "$schema" "$f" | sed 's/^/  /'
  # shellcheck disable=SC2016  # $p is a jq variable, not a shell expansion
  jq_filter='[inputs as $p | {key: ($p|tostring), value: ($inst[0]|getpath($p))}] | from_entries'
  echo "--- fetch occurrences command ---"
  echo "python \"$(rel_path "$SCRIPT_DIR/schema_occurrences.py")\" \"$schema_ptr\" \"$(rel_path "$schema")\" \"$(rel_path "$f")\" \\"
  echo "  | jq -n --slurpfile inst \"$(rel_path "$f")\" \\"
  echo "    '$jq_filter'"
}

on_success() {
  local f="$1" schema="$2"
  echo "--- recommendations ---"
  python "$REPO_DIR/src/test/conversation-exports/schema_recommendations.py" "$f" "$schema"
}

validate_file() {
  local f="$1" schema="$2" out="$3"
  {
    date -Iseconds
    file_info "$f"
    file_info "$schema"
    local python_out
    python_out="$(python "$REPO_DIR/src/main/validate.py" "$f" "$schema")"
    echo "$python_out"
    if ! echo "$python_out" | grep -qx "Valid!"; then
      on_failure "$f" "$schema" "$python_out"
    else
      on_success "$f" "$schema"
    fi
  } > "$out"
}

validate_export() {
  local conversation_export="${1%/}"
  local validation_dir
  validation_dir="$OUTPUT_DIR/$(basename "$conversation_export")/validation"

  rm -rf "$validation_dir"
  mkdir -p "$validation_dir"

  for f in "$conversation_export"/*.json; do
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
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  grep "^# " "$0" | sed "s/^# //" | head -10
  exit 0
fi

main() {
  local conversation_export="" conversation_exports=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --conversation-export)  conversation_export="$2";  shift 2 ;;
      --conversation-exports) conversation_exports="$2"; shift 2 ;;
      *) echo "Unknown argument: $1"
         echo "Usage: $0 --conversation-export <path> | --conversation-exports <path>"
         echo "       Pass --help for more information."; exit 1 ;;
    esac
  done

  if [[ -z "$conversation_export" && -z "$conversation_exports" ]]; then
    echo "Usage: $0 --conversation-export <path/to/data-directory>"
    echo "       $0 --conversation-exports <path/to/conversation-exports>"
    echo "       Pass --help for more information."
    exit 1
  fi

  # shellcheck source=/dev/null
  source ~/venvs/general/bin/activate

  if [[ -n "$conversation_export" ]]; then
    validate_export "$(cd "$conversation_export" && pwd)"
  else
    for d in "$(cd "$conversation_exports" && pwd)"/data-*/; do
      validate_export "$d"
    done
  fi

  deactivate
}

main "$@"
