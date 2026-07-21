#!/usr/bin/env python
"""
cache.py — the `yoga cache` dispatcher. `cache` is a NOUN: the rebuildable cache/
tier. Bare shows its state and writes nothing; the verbs do the work.

    ./yoga cache                    # status: the cache/ subtrees present
    ./yoga cache clean --dry-run    # report orphaned cache/ subtrees (neither written nor read)
    ./yoga cache clean --apply      # remove them
    ./yoga cache sync [--dry-run]   # rebuild cache/ by running each registry row's producers

Thin verb router over the sibling implementations — src/main/cli/clean.py and
src/main/cli/sync.py — so the CLI table carries one `cache` command whose verbs
are the two halves of the reproduction ritual: `yoga cache clean --apply &&
yoga cache sync` gives a fresh cache/ from input/ + output/ alone. `sync` is the
idempotent regenerator (L1); `clean` is the only destructive verb.
STDLIB-ONLY, like everything it routes to.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
VERBS = {'clean': 'clean.py', 'sync': 'sync.py'}
USAGE = (__doc__ or '').strip()


def status() -> int:
    """The bare-noun default: show current state, write nothing."""
    cache = REPO / 'cache'
    subs = sorted(p.name for p in cache.iterdir() if p.is_dir()) if cache.is_dir() else []
    print(f'cache/: {len(subs)} subtree(s) present' + (f': {", ".join(subs)}' if subs else ' (empty)'))
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ('--help', '-h'):
        print(USAGE)
        return 0
    if len(sys.argv) < 2:
        return status()               # bare noun → status, never an action
    verb = sys.argv[1]
    target = VERBS.get(verb)
    if target is None:
        # Derived from VERBS, the dispatch itself — never a second hand-written copy.
        # The flags belong to the verbs, so they are asked of the verbs, not restated here.
        print(f"error: unknown verb {verb!r} — takes: {' | '.join(VERBS)} "
              f"(bare: status; `yoga cache <verb> -h` for its flags)", file=sys.stderr)
        return 1
    # execv replaces the process — the verb's own exit status is the exit status
    os.execv(sys.executable, [sys.executable, str(HERE / target), *sys.argv[2:]])


if __name__ == '__main__':
    raise SystemExit(main())
