#!/usr/bin/env bash
# rsc/migration/672.sh - a family's catalogue sits under tmp/cache/model/catalogue at the
# family's address (#672); the flat directories keyed by a family's last segment, and the
# versions no sync ever removed from them, are discarded. corpus-yoga model sync rebuilds.
set -euo pipefail
SELF='rsc/migration/672.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

discard tmp/cache/model/apiConversation
discard tmp/cache/model/chatCategories
discard tmp/cache/model/conversations
discard tmp/cache/model/login_history
discard tmp/cache/model/manifest
discard tmp/cache/model/markdownConversation
discard tmp/cache/model/mcpMessage
discard tmp/cache/model/memories
discard tmp/cache/model/projectMemory
discard tmp/cache/model/projects
discard tmp/cache/model/semanticConcepts
discard tmp/cache/model/session
discard tmp/cache/model/sessionConversation
discard tmp/cache/model/users
