#!/usr/bin/env bash
# Pre-commit hook wrapper. Install with:
#   cp src/test/pre_commit.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
set -euo pipefail
GIT_HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$GIT_HOOKS_DIR/../run_python_script.sh" "$GIT_HOOKS_DIR/pre_commit.py"
