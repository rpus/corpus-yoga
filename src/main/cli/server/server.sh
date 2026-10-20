#!/usr/bin/env bash
# Local HTTP server for browsing and searching markdown files, with LaTeX rendering.
#
# Usage:
#   src/main/cli/server/server.sh                 # status: daemon + render-asset presence
#   src/main/cli/server/server.sh start [--markdown <dir>] [--port <n>] [--daemon]
#   src/main/cli/server/server.sh stop
#   src/main/cli/server/server.sh ensure-assets   # fetch the render libs into ext/lib/, then exit
#
# Defaults: --markdown data/output/markdown (the corpus the server exists to serve), --port 8182.

set -euo pipefail

SELF='src/main/cli/server/server.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }
# shellcheck source=src/main/tier.sh
source "$REPO_DIR/src/main/tier.sh"
# shellcheck source=src/main/cli/parse_argv.sh
source "$REPO_DIR/src/main/cli/parse_argv.sh"
# shellcheck source=src/main/report.sh
source "$REPO_DIR/src/main/report.sh"   # effect - what an act reports after its lines (issues/876)
# The record of the act is the launcher's tee (issues/708), tmp/logs/server/start/<stamp>.log. The
# daemon outlives the act and writes beside it: one immutable artifact per start (issues/370),
# stamped, colon-free, named <stamp>.daemon by the launcher's stamp, never as the record.
LOG_FILE="$TMP_DIR/logs/server/start/$(stamp_of server start).daemon"
PY=("$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/model/serve_markdown.py")

# print only the leading usage block (comment lines until the first non-comment line),
# not every '# ' comment in the file
help() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; }

start() {
  local daemon=0 have_md=0 pyargs=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --daemon) daemon=1; shift ;;
      *) [[ "$1" == "--markdown" ]] && have_md=1; pyargs+=("$1"); shift ;;
    esac
  done
  [[ "$have_md" -eq 0 ]] && pyargs+=(--markdown "$DATA_DIR/output/markdown")
  mkdir -p "$(dirname "$LOG_FILE")"
  export PYTHONUNBUFFERED=1
  if [[ "$daemon" -eq 1 ]]; then
    nohup "${PY[@]}" "${pyargs[@]}" > "$LOG_FILE" 2>&1 &
    sleep 1
    head -1 "$LOG_FILE"
    effect "server start: DONE - serving in the background; the daemon writes ${LOG_FILE#"$REPO_DIR/"}" "corpus-yoga server stop" "stops it"
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
  "")             exec "$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/main/cli/server/status.py" ;;   # bare noun → status; there is no `status` verb (this IS it)
  -h|--help|help) help ;;
  start)          shift; parse_argv server start "$@"; start "$@" ;;
  stop)           shift; parse_argv server stop "$@"; stop ;;
  ensure-assets)  shift; parse_argv server ensure-assets "$@"; "${PY[@]}" --ensure-assets ;;
  *) echo "server: unknown verb '${1}' — expected start, stop, ensure-assets (bare: status)" >&2; help; exit 1 ;;
esac
