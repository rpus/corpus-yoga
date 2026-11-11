#!/usr/bin/env bash
# rsc/migration/1047.sh - each pipeline is named for the noun whose promote deposits its
# input, and the schemas' metamodel is named so (issues/1047): the three pipelines' cache
# roots take their names, and the metamodel's cache, which corpus-yoga metamodel derive
# rebuilds under tmp/cache/metamodel, is discarded at its former name.
set -euo pipefail
SELF='rsc/migration/1047.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

move tmp/cache/chat-capture tmp/cache/browser
move tmp/cache/chat-export tmp/cache/export
move tmp/cache/code-transport tmp/cache/agent
discard tmp/cache/model
