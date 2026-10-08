#!/usr/bin/env bash
# rsc/migration/815.sh - the stage's rehearsal record is one file, tmp/stage/rehearsal.json
# (#815). A room's tmp/stage/rehearsal/ from before is a directory of stamped rehearsals,
# each the derived tiers of one run - verdicts and preview that corpus-yoga pipeline rehearse
# remakes under tmp/stage/scratch - so each is discarded and the directory retires with them.
set -euo pipefail
SELF='rsc/migration/815.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

for stamp in tmp/stage/rehearsal/*/; do
  [[ -d "$stamp" ]] || continue
  discard "${stamp%/}"
done
retire tmp/stage/rehearsal
