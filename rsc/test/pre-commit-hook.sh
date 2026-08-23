#!/usr/bin/env bash
# The accepted pre-commit hook. `corpus-yoga test install-hook` copies this file verbatim, and
# both `corpus-yoga prerequisites` and the gate byte-compare the installed hook against it — so
# "is the hook current" is decided by equality with this file, not by a pattern a longer
# or conditional hook could also satisfy.
#
# It names the COMMAND: a symlink to an implementation dangles the moment that file is
# renamed, and git skips a hook it cannot resolve without a word, so the gate fails OPEN.
# Which file serves `corpus-yoga test run` is the CLI's business.
#
# --show-toplevel, never this file's location: the COMMITTING tree is gated, so a commit
# made in a worktree runs the worktree's own gate.
exec "$(git rev-parse --show-toplevel)/corpus-yoga" test run "$@"
