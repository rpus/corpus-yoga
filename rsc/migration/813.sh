#!/usr/bin/env bash
# rsc/migration/813.sh - the command prerequisites is status (issues/807), and an enacting verb
# logs under tmp/logs/<command>/<verb>/ (issues/453): the runs of prerequisites sync move to
# where status sync writes.
set -euo pipefail
SELF='rsc/migration/813.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

move tmp/logs/prerequisites tmp/logs/status
