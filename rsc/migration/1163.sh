#!/usr/bin/env bash
# rsc/migration/1163.sh - the stage is laid out as the checkout is (issues/1163): its input, at
# stage/input, folds into stage/data/input, where a capture by the new code may already have
# written; the last rehearsal's run, kept under stage/scratch - its data/input a link to that
# input - moves to stage/data/output, stage/cache and stage/logs, its working files and the link
# discarded; the rehearsal record stands where it stood, at stage/rehearsal.json.
set -euo pipefail
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

fold stage/input stage/data/input
sever stage/scratch/data/input
move stage/scratch/data/output stage/data/output
move stage/scratch/cache stage/cache
move stage/scratch/logs stage/logs
discard stage/scratch/tmp
discard stage/scratch/extent.json
retire stage/scratch/data
retire stage/scratch
