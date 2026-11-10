#!/usr/bin/env bash
# rsc/migration/672.sh - a family's catalogue sits under tmp/cache/metamodel/catalogue at the
# family's address (issues/672); the flat directories keyed by a family's last segment, and the
# versions no sync ever removed from them, are discarded. corpus-yoga metamodel derive rebuilds.
set -euo pipefail
SELF='rsc/migration/672.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

discard tmp/cache/metamodel/apiConversation
discard tmp/cache/metamodel/chatCategories
discard tmp/cache/metamodel/conversations
discard tmp/cache/metamodel/login_history
discard tmp/cache/metamodel/manifest
discard tmp/cache/metamodel/markdownConversation
discard tmp/cache/metamodel/mcpMessage
discard tmp/cache/metamodel/memories
discard tmp/cache/metamodel/projectMemory
discard tmp/cache/metamodel/projects
discard tmp/cache/metamodel/semanticConcepts
discard tmp/cache/metamodel/session
discard tmp/cache/metamodel/sessionConversation
discard tmp/cache/metamodel/users
