#!/usr/bin/env bash
# Run the repo-wide cross-reference audit.
# Output: gen/xref.csv
#
# Usage:
#   src/test/xref.sh --data-root <path>     # repo-wide scan
#   src/test/xref.sh --out <path>           # override output path (default: gen/xref.csv)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 --data-root <path>"
  echo "       Pass --help for more information."
  exit 1
fi

# shellcheck source=/dev/null
source ~/venvs/general/bin/activate
python "$SCRIPT_DIR/xref.py" "$@"
deactivate
