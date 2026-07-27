#!/usr/bin/env bash
# Local HTTP server for browsing and searching markdown files, with LaTeX rendering.
#
# Usage:
#   src/main/model/server.sh                 # status: daemon + render-asset presence
#   src/main/model/server.sh start [--markdown <dir>] [--port <n>] [--daemon]
#   src/main/model/server.sh stop
#   src/main/model/server.sh ensure-assets   # fetch the render libs into tmp/cache/, then exit
#
# Defaults: --markdown data/output/markdown (the corpus the server exists to serve), --port 8182.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
# run diagnostics live under tmp/logs/ (time-keyed, human-facing); tmp/cache/ holds only
# datum-keyed derived state (validation logs are memoisation + matrix input)
LOG_FILE="$REPO_DIR/tmp/logs/server/start.log"
PY=("$SCRIPT_DIR/../../run_python_script.sh" "$SCRIPT_DIR/serve_markdown.py")

# print only the leading usage block (comment lines until the first non-comment line),
# not every '# ' comment in the file
help() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; }

status() {
  local pid
  pid="$(pgrep -f 'serve_markdown.py' 2>/dev/null | head -1 || true)"
  if [[ -n "$pid" ]]; then
    echo "serve_markdown daemon: running (pid $pid)"
  else
    echo "serve_markdown daemon: not running"
  fi
  # render-asset presence — a bare file tally against the manifest (the authoritative
  # readiness report, with versions, is src/prerequisites.sh's check_dependencies)
  local manifest="$SCRIPT_DIR/serve_assets.txt" dir="$REPO_DIR/tmp/cache/serve_markdown"
  local total=0 present=0 line f
  while IFS= read -r line; do
    line="${line%%#*}"; f="${line%%[[:space:]]*}"
    [[ -z "$f" ]] && continue
    total=$((total + 1)); [[ -f "$dir/$f" ]] && present=$((present + 1))
  done < "$manifest"
  echo "render assets: $present/$total present in tmp/cache/serve_markdown"
  echo "verbs: start | stop | ensure-assets    (yoga server --help)"
}

start() {
  local daemon=0 have_md=0 pyargs=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --daemon) daemon=1; shift ;;
      *) [[ "$1" == "--markdown" ]] && have_md=1; pyargs+=("$1"); shift ;;
    esac
  done
  [[ "$have_md" -eq 0 ]] && pyargs+=(--markdown "$REPO_DIR/data/output/markdown")
  mkdir -p "$(dirname "$LOG_FILE")"
  export PYTHONUNBUFFERED=1
  if [[ "$daemon" -eq 1 ]]; then
    nohup "${PY[@]}" "${pyargs[@]}" > "$LOG_FILE" 2>&1 &
    sleep 1
    head -1 "$LOG_FILE"
    echo "Stop with: yoga server stop"
    echo "Logs: $LOG_FILE"
  else
    "${PY[@]}" "${pyargs[@]}"
  fi
}

stop() {
  if pkill -f 'serve_markdown.py' 2>/dev/null; then
    echo "Stopped"
  else
    echo "No serve_markdown.py process found"
  fi
}

case "${1:-}" in
  "")             status ;;   # bare noun → status; there is no `status` verb (this IS it)
  -h|--help|help) help ;;
  start)          shift; start "$@" ;;
  stop)           stop ;;
  ensure-assets)  "${PY[@]}" --ensure-assets ;;
  *) echo "server: unknown verb '${1}' — expected start, stop, ensure-assets (bare: status)" >&2; help; exit 1 ;;
esac
