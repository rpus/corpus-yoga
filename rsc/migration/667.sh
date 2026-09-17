#!/usr/bin/env bash
# rsc/migration/667.sh - a pipeline is named <channel>-<act>, singular, and reads the
# directories of data/input that end in its act (#667): the two chat capture directories
# and the three pipelines' cache roots take their names.
set -euo pipefail
SELF='rsc/migration/667.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

move data/input/claude/chat/browser-API data/input/claude/chat/API-capture
move data/input/gemini/chat/browser-DOM data/input/gemini/chat/DOM-capture
move tmp/cache/browser-captures tmp/cache/chat-capture
move tmp/cache/chat-exports tmp/cache/chat-export
move tmp/cache/code-agents tmp/cache/code-transport
