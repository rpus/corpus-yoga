#!/usr/bin/env bash
# Generate per-schema definition catalogues as candidates for rsc/schema/model.json.
# Usage: src/test/gen_model.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/../run_python_script.sh" "$SCRIPT_DIR/gen_model.py"
