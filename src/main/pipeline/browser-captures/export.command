#!/usr/bin/env bash
# Terminal-hosted trigger for export.applescript — what the macOS Shortcut runs.
#
# The Shortcut's entire shell line is: open -a Terminal <this file>. Shortcuts'
# own shell runs under ShortcutsMacHelper, a framework XPC service that macOS
# TCC silently denies (no prompt, ever) on protected folders — ~/Downloads,
# and the data/input/ data home wherever it resolves into ~/Documents. Terminal
# already holds those grants from everyday CLI use, so delegating execution
# here keeps one permission regime and one code path, and makes every capture
# run visible in a window instead of a notification-sized black box.
#
# Usage:
#   open -a Terminal src/main/pipeline/browser-captures/export.command   # what the Shortcut does
#   src/main/pipeline/browser-captures/export.command                    # identical direct run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec caffeinate -dim osascript "$SCRIPT_DIR/export.applescript"
