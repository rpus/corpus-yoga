#!/usr/bin/env bash
# rsc/migration/1170.sh - the machine-local roots are named for what they hold (issues/1170):
# tmp/cache, tmp/logs and tmp/stage fold into cache, logs and stage beside data, the new code
# having begun to write there; each provider's chat listing moves from tmp/browser/fetch to
# fetch/<provider>/chat/listing.json, at its chats' address in the store, and upstream's
# references from tmp/reference/fetch to fetch/reference; a stage scratch's cache and logs, kept
# under its tmp, move beside its data; tmp/cache/scratch, the working files of runs long gone, is
# discarded, and so is tmp/cache/python, the bytecode python rebuilds, which the new code has already
# written again under cache/python. tmp keeps what lasts one run.
set -euo pipefail
SELF='rsc/migration/1170.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

discard tmp/cache/scratch
discard tmp/cache/python
for scratch in tmp/stage/*/scratch; do
  [[ -d "$scratch" ]] || continue
  move "$scratch/tmp/cache" "$scratch/cache"
  move "$scratch/tmp/logs" "$scratch/logs"
done
fold tmp/cache cache
fold tmp/logs logs
fold tmp/stage stage
for listing in tmp/browser/fetch/*.json; do
  [[ -e "$listing" ]] || continue
  provider="${listing##*/}"
  move "$listing" "fetch/${provider%.json}/chat/listing.json"
done
retire tmp/browser/fetch
retire tmp/browser
move tmp/reference/fetch fetch/reference
retire tmp/reference
