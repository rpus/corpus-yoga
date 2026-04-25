#!/usr/bin/env bash
# Generate per-schema definition catalogues as candidates for rsc/model.json.
# Output goes to gen/model/ for review; rsc/model.json is hand-curated from these.
#
# Usage:
#   src/test/gen_model.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT_DIR="$REPO_DIR/gen/model"
mkdir -p "$OUT_DIR"

# shellcheck source=/dev/null
source ~/venvs/general/bin/activate

# Auto-detect the latest conversations schema (highest semver).
LATEST_CONV=$(python3 -c "
import re
from pathlib import Path
schemas = sorted(
    Path('$REPO_DIR/rsc/schema/conversations').glob('v*.json'),
    key=lambda f: [int(x) for x in re.findall(r'\d+', f.stem)]
)
print(schemas[-1])
")

python "$SCRIPT_DIR/gen_model_candidate.py" conversations \
    "$LATEST_CONV" \
    > "$OUT_DIR/conversations.json"
echo "  ✓ gen/model/conversations.json  (from $(basename "$LATEST_CONV"))"

for schema in memories projects users; do
    python "$SCRIPT_DIR/gen_model_candidate.py" "$schema" \
        "$REPO_DIR/rsc/schema/$schema/$schema.json" \
        > "$OUT_DIR/$schema.json"
    echo "  ✓ gen/model/$schema.json"
done

deactivate
echo "Review gen/model/ and update rsc/model.json as needed."
