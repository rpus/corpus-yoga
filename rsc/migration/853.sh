#!/usr/bin/env bash
# rsc/migration/853.sh - a live store mounts at ext/mnt/<provider>/code/machine-transport/<machine>,
# the address its units have under tmp/stage/input and data/input (issues/853); the link each
# provider had at ext/mnt/agent/<provider> moves there, and ext/mnt/agent retires.
# corpus-yoga agent mount --apply creates the current links.
set -euo pipefail
SELF='rsc/migration/853.sh'
# shellcheck source=rsc/migration/step.sh
source "${BASH_SOURCE[0]%/*}/step.sh"

for link in ext/mnt/agent/*; do
  [[ -L "$link" ]] || continue
  machine="$(tr -cd 'A-Za-z0-9_-' < machine-name.txt 2>/dev/null || true)"
  [[ -n "$machine" ]] || { echo "FAIL: machine-name.txt binds no machine, and the mount carries the machine - corpus-yoga status says how to bind one" >&2; exit 1; }
  move "$link" "ext/mnt/${link##*/}/code/machine-transport/$machine"
done
retire ext/mnt/agent
