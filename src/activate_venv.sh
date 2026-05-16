#!/usr/bin/env bash
# Source this file to activate the project venv.
# Sets trap deactivate EXIT so callers need not call deactivate manually.
# Override the path: VENV=/other/path source src/activate_venv.sh

: "${VENV:=$HOME/venvs/general}"

if [[ ! -f "$VENV/bin/activate" ]]; then
    echo "error: venv not found at $VENV" >&2
    echo "       python3 -m venv \$VENV && pip install -r src/requirements.txt" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"
trap deactivate EXIT
