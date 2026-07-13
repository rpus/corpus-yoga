#!/usr/bin/env bash
# Ensures input/code-projects is a symlink to ~/.claude/projects.
#
# Usage:
#   src/main/code-agents/PREP.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) grep "^# " "$0" | sed "s/^# //"; exit 0 ;;
      *) echo "Unknown argument: $1"; echo "Pass --help for more information."; exit 1 ;;
    esac
  done
}

link_projects() {
  mkdir -p "$REPO_DIR/input"
  ln -sfn ~/.claude/projects "$REPO_DIR/input/code-projects"
}

main() {
  parse_args "$@"
  echo "${SCRIPT_DIR#"$REPO_DIR/"}/$(basename "$0")"

  link_projects
}

main "$@"
