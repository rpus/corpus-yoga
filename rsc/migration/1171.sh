#!/usr/bin/env bash
# rsc/migration/1171.sh - the stage is one directory, stage/ (issues/1171): the room's stage, laid out
# by issues/1133 and issues/1170 as stage/usr, moves up a level - its input folded into stage/input,
# where a capture by the new code may already have written, and its scratch and rehearsal record
# moved beside it - and stage/dev, the dev gate's, which every gate run made afresh and the gate now
# keeps under tmp/ for the length of its run, is discarded with every empty directory it held.
set -euo pipefail
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

fold stage/usr/input stage/input
move stage/usr/scratch stage/scratch
move stage/usr/rehearsal.json stage/rehearsal.json
retire stage/usr
discard stage/dev
