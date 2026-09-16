#!/usr/bin/env bash
# rsc/migration/636.sh - the live agent stores mount at ext/mnt/agent/<provider> (#636);
# the links the earlier layouts left are removed. corpus-yoga agent mount --apply
# creates the current links.
set -euo pipefail
SELF='rsc/migration/636.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

remove ext/claude-code-projects
remove ext/mnt/claude-code-projects
remove ext/mnt/gemini-antigravity
