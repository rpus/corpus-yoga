#!/usr/bin/env bash
# Ensures ext/mnt/<mount> is a symlink to each declared provider's live session
# store where that store exists (rsc/provider/providers.csv; ext/mnt/ is the
# by-reference species: mounts of state other systems own).
#
# Usage:
#   src/main/pipeline/code-agents/link_projects.sh

set -euo pipefail

SELF='src/main/pipeline/code-agents/link_projects.sh'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SCRIPT_DIR%/"${SELF%/*}"}"
[[ "${REPO_DIR}/$SELF" -ef "${BASH_SOURCE[0]}" ]] || { echo "${BASH_SOURCE[0]}: not at its declared address $SELF" >&2; exit 1; }

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

link_projects() {
  mkdir -p "$REPO_DIR/ext/mnt"
  local provider live mount rows
  rows="$("$REPO_DIR/src/run_python_script.sh" -c 'import sys; sys.path.insert(0, sys.argv[1]); import provider; print(provider.lines())' "$REPO_DIR/src/main")" || exit 1
  while IFS=$'\x1f' read -r provider _ live mount _ _; do
    [[ -n "$provider" && -n "$live" && -n "$mount" ]] || continue
    live="${live/#\~/$HOME}"
    [[ -d "$live" ]] || continue
    ln -sfn "$live" "$REPO_DIR/ext/mnt/$mount"
    echo "ext/mnt/$mount → ${live/#$HOME/~}"
  done <<< "$rows"
  # the pre-species address; a link is re-creatable state, so retiring it here is
  # the script doing its one job at the new address rather than leaving two names
  if [[ -L "$REPO_DIR/ext/claude-code-projects" ]]; then
    rm "$REPO_DIR/ext/claude-code-projects"
    echo "retired ext/claude-code-projects (now ext/mnt/claude-code-projects)"
  fi
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  link_projects
}

main "$@"
