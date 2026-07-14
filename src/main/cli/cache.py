#!/usr/bin/env python
"""
cache.py — the `yoga cache` dispatcher: the cache/ lifecycle verbs.

    ./yoga cache clean --dry-run    # report orphaned cache/ subtrees (neither written nor read)
    ./yoga cache clean --apply      # remove them
    ./yoga cache regen [--dry-run]  # rebuild cache/ by running each registry row's producers

Thin verb router over the sibling implementations — src/main/cli/clean.py and
src/main/cli/regen.py — so the CLI table carries one `cache` command whose verbs
are the two halves of the reproduction ritual: `yoga cache clean --apply &&
yoga cache regen` gives a fresh cache/ from input/ + output/ alone.
STDLIB-ONLY, like everything it routes to.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERBS = {'clean': 'clean.py', 'regen': 'regen.py'}
USAGE = (__doc__ or '').strip()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ('--help', '-h'):
        print(USAGE)
        return 0
    if len(sys.argv) < 2:
        print(USAGE)
        return 1
    verb = sys.argv[1]
    target = VERBS.get(verb)
    if target is None:
        print(f"error: unknown verb {verb!r} — takes: clean (--dry-run | --apply) | regen [--dry-run]",
              file=sys.stderr)
        return 1
    # execv replaces the process — the verb's own exit status is the exit status
    os.execv(sys.executable, [sys.executable, str(HERE / target), *sys.argv[2:]])


if __name__ == '__main__':
    raise SystemExit(main())
