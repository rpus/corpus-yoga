#!/usr/bin/env bash
# rsc/migration/635.sh - the agent cache holds a directory per provider (issues/635):
# tmp/cache/agent/<provider>/<machine>/... A room's cache from before held
# claude's machines directly under the root; each moves under claude, its logs with it,
# so nothing revalidates. A directory named for a provider's mechanism is already one.
set -euo pipefail
SELF='rsc/migration/635.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

for machine in tmp/cache/agent/*/; do
  [[ -d "$machine" ]] || continue
  machine="$(basename "$machine")"
  [[ -d "src/main/agent/$machine" ]] && continue
  move "tmp/cache/agent/$machine" "tmp/cache/agent/claude/$machine"
done
