#!/usr/bin/env bash
# Fetch the live API JSON for each conversation in a browser-captures batch.
# Requires Safari open and logged into claude.ai.
#
# Usage:
#   ./src/main/browser-captures/safari_fetch_api_json.sh --captures     ../browser-captures/data-<...>
#   ./src/main/browser-captures/safari_fetch_api_json.sh --captures-root ../browser-captures

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/../../activate_venv.sh"

caffeinate -dim python3 "$SCRIPT_DIR/safari_fetch_api_json.py" "$@"
