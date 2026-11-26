#!/usr/bin/env bash
# rsc/migration/1181.sh - every subtree of the cache is named for the command that writes it
# (issues/1181): each pipeline's cache, which corpus-yoga pipeline writes, moves from
# cache/<pipeline> to cache/pipeline/<pipeline>, folded where the new code has already written -
# the room's and the stage's alike. Every other subtree stands where it stood.
set -euo pipefail
SELF='rsc/migration/1181.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

for root in cache stage/cache; do
  for pipeline in agent browser export; do
    fold "$root/$pipeline" "$root/pipeline/$pipeline"
  done
done
