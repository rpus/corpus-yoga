#!/usr/bin/env bash
# rsc/migration/655.sh - the indexing command's files read state then kind under
# data/output/indexing (#655, #656), and the dashboard root retires with them.
set -euo pipefail
SELF='rsc/migration/655.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

move data/output/dashboard/semantic-concepts.json data/output/indexing/inferred-semantic-concepts.json
move data/output/dashboard/chat-categories.json data/output/indexing/inferred-chat-categories.json
retire data/output/dashboard
move data/output/indexing/accepted.txt data/output/indexing/accepted-semantic-concepts.txt
move data/output/indexing/rejected.txt data/output/indexing/rejected-semantic-concepts.txt
move tmp/cache/indexing/candidates.txt tmp/cache/indexing/candidate-semantic-concepts.txt
