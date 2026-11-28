#!/usr/bin/env bash
# rsc/migration/1192.sh - each unit's run output stands at the unit's own input address under
# cache/pipeline (issues/1192): browser's claude and gemini captures, agent's claude and gemini
# sessions and export's batches move from beneath their pipeline's name to their store's input address,
# folded where the new code has already written - in the room's cache and the stage's alike. Whatever
# stands beneath a pipeline's name outside a provider is no unit's, and stays for corpus-yoga cache to name.
set -euo pipefail
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

for root in cache/pipeline stage/cache/pipeline; do
  fold "$root/browser/claude" "$root/claude/chat/API-capture"
  fold "$root/browser/gemini" "$root/gemini/chat/DOM-capture"
  fold "$root/agent/claude" "$root/claude/code/machine-transport"
  fold "$root/agent/gemini" "$root/gemini/code/machine-transport"
  fold "$root/export" "$root/claude/chat/bulk-export"
done
