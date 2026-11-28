#!/usr/bin/env bash
# rsc/migration/1189.sh - the book index is built from the capture in use, with no candidates to
# judge (issues/1189): the judgement's records - the accepted headwords, the rejected concepts and
# the candidate list - retire with the verbs that wrote them, each counted on the line before it goes.
set -euo pipefail
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

dispose data/output/indexing/accepted-semantic-concepts.txt
dispose data/output/indexing/rejected-semantic-concepts.txt
dispose cache/indexing/candidate-semantic-concepts.txt
