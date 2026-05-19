#!/usr/bin/env bash
# Ensure prerequisites are in place before running the pipelines.
#
# 1. Locates Python 3 (tries python3, then python)
# 2. Creates the project venv if absent: ~/venvs/general (override: VENV=<path>)
# 3. Installs dependencies from src/requirements.txt into the venv
#
# Safe to re-run.
#
# Usage:
#   ./PREP.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${VENV:=$HOME/venvs/general}"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

require_cmd() {
  local cmd="$1" hint="$2"
  if ! command -v "$cmd" &>/dev/null; then
    echo "error: $cmd not found — $hint" >&2
    exit 1
  fi
}

find_python3() {
  if command -v python3 &>/dev/null; then
    echo "python3"; return 0
  fi
  if command -v python &>/dev/null; then
    if python --version 2>&1 | grep -q "^Python 3"; then
      echo "python"; return 0
    fi
  fi
  echo "error: Python 3 not found — install via: brew install python" >&2
  return 1
}

ensure_venv() {
  local python="$1"
  if [[ ! -f "$VENV/bin/activate" ]]; then
    echo "creating venv at $VENV"
    "$python" -m venv "$VENV"
  fi
}

install_deps() {
  # shellcheck source=/dev/null
  source "$VENV/bin/activate"
  pip install -q -r "$SCRIPT_DIR/src/requirements.txt"
}

main() {
  parse_args "$@"
  basename "$0"

  require_cmd jq "install via: brew install jq"
  local python; python="$(find_python3)"
  ensure_venv "$python"
  install_deps

  mkdir -p "$SCRIPT_DIR/ext"
}

main "$@"
