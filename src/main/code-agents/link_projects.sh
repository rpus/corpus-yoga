#!/usr/bin/env bash
# Ensures ext/mnt/claude-code-projects is a symlink to ~/.claude/projects
# (ext/mnt/ is the by-reference species: mounts of state other systems own).
#
# Usage:
#   src/main/code-agents/link_projects.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

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
  ln -sfn ~/.claude/projects "$REPO_DIR/ext/mnt/claude-code-projects"
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
