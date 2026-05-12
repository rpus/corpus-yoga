#!/usr/bin/env bash
# Local markdown viewer for Claude conversation browser captures.
#
# Usage:
#   src/main/model/search_proxy.sh [--port 8182]
#   src/main/model/search_proxy.sh --daemon [--port 8182]
#   src/main/model/search_proxy.sh stop

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOG_FILE="$REPO_DIR/gen/search_proxy.log"

if [[ "${1:-}" == "stop" ]]; then
  if pkill -f 'search_proxy.py' 2>/dev/null; then
    echo "Stopped"
  else
    echo "No search_proxy.py process found"
  fi
  exit 0
fi

DAEMON=0
declare -a ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --daemon) DAEMON=1; shift ;;
    *)        ARGS+=("$1"); shift ;;
  esac
done

mkdir -p "$REPO_DIR/gen"
export PYTHONUNBUFFERED=1

if [[ "$DAEMON" -eq 1 ]]; then
  nohup "$SCRIPT_DIR/../../run_python_script.sh" "$SCRIPT_DIR/search_proxy.py" ${ARGS[@]+"${ARGS[@]}"} \
    > "$LOG_FILE" 2>&1 &
  sleep 1
  echo "Started — logs: $LOG_FILE"
  echo "Stop with: $0 stop"
else
  "$SCRIPT_DIR/../../run_python_script.sh" "$SCRIPT_DIR/search_proxy.py" ${ARGS[@]+"${ARGS[@]}"}
fi
