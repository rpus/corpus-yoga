#!/usr/bin/env bash
# Run the full file audit for one export: build the normalised CSV and joined
# table (audit_files.py), then run all SQL queries against them (query_files.py).
#
# Usage:
#   src/test/audit_files.sh <export-name>
#
# Example:
#   src/test/audit_files.sh \
#       data-0fc4c1e0-4719-4e10-997a-697bf05599af-1776950570-e265d361-batch-0000
#
# Output: gen/<export>/audit_queries/

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <export-name>"
  exit 1
fi

# shellcheck source=/dev/null
source ~/venvs/general/bin/activate
python "$SCRIPT_DIR/audit_files.py" "$1"
python "$SCRIPT_DIR/query_files.py" "$1"
deactivate
