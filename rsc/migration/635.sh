#!/usr/bin/env bash
# rsc/migration/635.sh - the code-transport cache holds a directory per provider (#635):
# tmp/cache/code-transport/<provider>/<machine>/... A room's cache from before held
# claude's machines directly under the root; each moves under claude, its logs with it,
# so nothing revalidates. A directory named for a provider's mechanism is already one.
set -euo pipefail
SELF='rsc/migration/635.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

for machine in tmp/cache/code-transport/*/; do
  [[ -d "$machine" ]] || continue
  machine="$(basename "$machine")"
  [[ -d "src/main/pipeline/code-transport/$machine" ]] && continue
  move "tmp/cache/code-transport/$machine" "tmp/cache/code-transport/claude/$machine"
done
