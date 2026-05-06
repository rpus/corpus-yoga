#!/usr/bin/env bash
# Export every conversation in a bulk export to markdown via Safari automation.
# Requires Safari open, focused, and logged into claude.ai throughout.
#
# Usage:
#   ./src/main/browser-captures/safari_capture.sh --chat-export  ../chat-exports/data-<...>
#   ./src/main/browser-captures/safari_capture.sh --chat-exports ../chat-exports
# Output goes to ../browser-captures/<export-name>/<uuid>/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$SCRIPT_DIR/../../activate_venv.sh"

# caffeinate -dim: prevent display sleep (-d), idle sleep (-i), and disk sleep (-m)
caffeinate -dim python3 "$SCRIPT_DIR/safari_capture.py" "$@"
