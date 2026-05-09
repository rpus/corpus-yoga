#!/usr/bin/env bash
# Pre-commit hook wrapper. Install with:
#   ln -sfn ../../src/test/pre_commit.sh .git/hooks/pre-commit
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
mkdir -p "$REPO_DIR/gen"
"$REPO_DIR/src/run_python_script.sh" "$REPO_DIR/src/test/pre_commit.py" 2>&1 | tee "$REPO_DIR/src/test/pre_commit.log"
