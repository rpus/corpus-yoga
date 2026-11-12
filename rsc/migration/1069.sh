#!/usr/bin/env bash
# rsc/migration/1069.sh - a raise keeps the body it sent beside the act's record (issues/1069):
# each body a room holds under tmp/forge/raise moves to tmp/logs/forge/raise, and the emptied
# directory is retired.
set -euo pipefail
SELF='rsc/migration/1069.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

[[ -d tmp/forge/raise ]] || exit 0
for body in tmp/forge/raise/*; do
  [[ -e "$body" ]] || continue
  move "$body" "tmp/logs/forge/raise/${body##*/}"
done
retire tmp/forge/raise
