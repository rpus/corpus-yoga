#!/usr/bin/env bash
# Run a Python script in the project venv.
# Usage: src/run_python_script.sh <script.py> [args...]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/activate_venv.sh"
python "$@"
