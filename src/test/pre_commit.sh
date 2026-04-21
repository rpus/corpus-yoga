#!/usr/bin/env bash
# Pre-commit hook wrapper. Install with:
#   cp src/test/pre_commit.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit

set -euo pipefail
GIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=/dev/null
source ~/venvs/general/bin/activate
python "$GIT_DIR/../../src/test/pre_commit.py"
exit_code=$?
deactivate
exit $exit_code
