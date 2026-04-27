#!/usr/bin/env bash
# Run a Python script in the project venv.
# Usage: src/run_python_script.sh <script.py> [args...]

set -euo pipefail
# shellcheck source=/dev/null
source ~/venvs/general/bin/activate
python "$@"
exit_code=$?
deactivate
exit $exit_code
