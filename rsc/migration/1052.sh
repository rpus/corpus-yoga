#!/usr/bin/env bash
# rsc/migration/1052.sh - python's bytecode stands under tmp/cache/python (issues/1052): each
# __pycache__ a room's src holds from before is discarded - python rebuilds what it needs
# under the prefix - and each directory under src that held nothing else, the leaving of a
# module moved or removed, is retired, the deepest first.
set -euo pipefail
SELF='rsc/migration/1052.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

[[ -d src ]] || exit 0
while IFS= read -r bytecode; do
  discard "$bytecode"
done < <(find src -type d -name __pycache__ | sort)
while IFS= read -r dir; do
  [[ -z "$(find "$dir" -type f ! -path '*/__pycache__/*' ! -name .DS_Store -print -quit)" ]] || continue
  retire "$dir"
done < <(find src -mindepth 1 -type d ! -name __pycache__ ! -path '*/__pycache__/*' | sort -r)
