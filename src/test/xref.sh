#!/usr/bin/env bash
# Run the repo-wide cross-reference audit.
# Output: gen/xref.csv
#
# Usage:
#   src/test/xref.sh [--out <path>]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=/dev/null
source ~/venvs/general/bin/activate
python "$SCRIPT_DIR/xref.py" "$@"
deactivate
