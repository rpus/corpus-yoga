#!/usr/bin/env bash
# Local HTTP server for browsing and searching markdown files.
#
# Usage:
#   src/main/model/serve_markdown.sh --markdown <dir> [--port 8182]
#   src/main/model/serve_markdown.sh --markdown <dir> --daemon [--port 8182]
#   src/main/model/serve_markdown.sh stop

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOG_FILE="$REPO_DIR/gen/model/serve_markdown.log"

parse_args() {
  daemon=0
  args=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      --daemon)  daemon=1; shift ;;
      *)         args+=("$1"); shift ;;
    esac
  done
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  if [[ "${args[0]:-}" == "stop" ]]; then
    if pkill -f 'serve_markdown.py' 2>/dev/null; then
      echo "Stopped"
    else
      echo "No serve_markdown.py process found"
    fi
    return
  fi

  mkdir -p "$(dirname "$LOG_FILE")"
  export PYTHONUNBUFFERED=1

  if [[ "$daemon" -eq 1 ]]; then
    nohup "$SCRIPT_DIR/../../run_python_script.sh" "$SCRIPT_DIR/serve_markdown.py" ${args[@]+"${args[@]}"} \
      > "$LOG_FILE" 2>&1 &
    sleep 1
    head -1 "$LOG_FILE"
    echo "Stop with: $0 stop"
    echo "Logs: $LOG_FILE"
  else
    "$SCRIPT_DIR/../../run_python_script.sh" "$SCRIPT_DIR/serve_markdown.py" ${args[@]+"${args[@]}"}
  fi
}

main "$@"
