#!/usr/bin/env bash
# Shared helper: validate one JSON file against every v*.json in a schema directory.
# Source this from a pipeline validate.sh; requires REPO_DIR to be set by the caller.
#
# Usage:
#   source "$SCRIPT_DIR/../validate_versions.sh"
#   validate_versions INPUT_FILE SCHEMA_DIR LOG_DIR LABEL

validate_versions() {
  local input_file="$1" schema_dir="$2" log_dir="$3" label="$4"
  mkdir -p "$log_dir"
  for schema in "$schema_dir"/v*.json; do
    local version; version="$(basename "${schema%.json}")"
    local log_out="$log_dir/$version.log"
    {
      date -Iseconds
      echo "$input_file: $(wc -l < "$input_file" | xargs) lines, $(wc -c < "$input_file" | xargs) bytes"
      echo "$schema: $(wc -c < "$schema" | xargs) bytes"
      python "$REPO_DIR/src/main/validate.py" "$input_file" "$schema"
    } > "$log_out"
    local status; status="$(grep -E '^Valid!|^Validation error' "$log_out" | head -1)"
    if [[ ${#status} -gt 80 ]]; then
      echo "  $label ($version): ${status:0:80}…"
      echo "    → $log_out"
    else
      echo "  $label ($version): $status"
    fi
  done
}
