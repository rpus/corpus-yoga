#!/usr/bin/env python
"""
clean.py — remove ORPHANED tmp/cache/ subtrees: paths the machinery neither writes
nor reads.

tmp/cache/ is the workshop — rebuildable derivations, every live subtree OWNED by a
pipeline (its validation/derivation tree) or an out-of-band command (its
output). A path under tmp/cache/ that is neither an owned subtree, nor inside one,
nor an ancestor of one (a parent kept only to reach owned children) is
RESIDUE: a former output whose producer moved or was renamed — e.g. the
projected markdown that moved to data/output/markdown/claude/chat/conversations, orphaning
tmp/cache/browser-captures/markdown; or a tmp/cache/<old-name>/ left by a pipeline rename.

"Not written AND not read" is the criterion — coverage by the machinery in
either direction is what makes a tmp/cache/ path live. Being derived, an orphan is
safe to remove (nothing regenerates it here); and even a mistaken removal of a
LIVE subtree costs only a pipeline re-run, never data — that is the tmp/cache/
contract (rsc/CALCULUS.md, the 'derived' class: always rebuildable).

The owned-set is DECLARED in rsc/cache_io.csv (via cache_io.py), shared with sync
and `yoga test run`'s check_cache_io — one registry, three consumers.

STDLIB-ONLY. One of --dry-run / --apply is REQUIRED: cleaning is deliberate,
never a default, and never a silent no-op.

Usage:
    yoga cache clean --dry-run   # list orphaned tmp/cache/ subtrees with sizes; remove nothing
    yoga cache clean --apply     # remove them
"""
import argparse
import shutil
import sys
from pathlib import Path

from cache_io import owned_paths

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from argparse_help import enrich

REPO = Path(__file__).resolve().parents[3]
CACHE = REPO / 'tmp' / 'cache'


def orphans(root: Path) -> list[Path]:
    """The tmp/cache/ entries the machinery neither writes nor reads. An entry is KEPT
    when it is owned (declared in rsc/cache_io.csv), inside an owned subtree (we
    never descend into owned dirs), or an ANCESTOR of one (descend to reach the
    owned child); everything else is returned as an orphan, without descending.
    Paths compare repo-relative (`tmp/cache/…`), matching the registry's cache_path."""
    owned = owned_paths()
    found: list[Path] = []

    def visit(d: Path) -> None:
        rel = d.relative_to(REPO).as_posix()
        if rel in owned:
            return  # owned subtree — keep whole, do not descend
        if any(o.startswith(rel + '/') for o in owned):
            for child in sorted(d.iterdir()):       # ancestor of an owned path
                visit(child)
            return
        found.append(d)  # neither owned, inside-owned, nor ancestor-of-owned

    for child in sorted(root.iterdir()):
        visit(child)
    return found


def _size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob('*') if f.is_file())


def _human(n: float) -> str:
    for unit in ('B', 'K', 'M'):
        if n < 1024:
            return f'{n:.0f}{unit}' if unit == 'B' else f'{n:.1f}{unit}'
        n /= 1024
    return f'{n:.1f}G'


def main() -> int:
    ap = argparse.ArgumentParser(description='remove orphaned tmp/cache/ subtrees (neither written nor read)')
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--apply', action='store_true')
    enrich(ap, 'cache', 'clean')
    args = ap.parse_args()

    if not CACHE.is_dir():
        print('no tmp/cache/ — nothing to clean')
        return 0

    found = orphans(CACHE)
    if not found:
        print('tmp/cache/ is clean — every subtree is written or read by a current step')
        return 0

    total = 0
    for p in found:
        n = _size(p)
        total += n
        rel = p.relative_to(REPO).as_posix()
        verb = 'orphan' if args.dry_run else 'removing'
        print(f'  {verb}: {rel}  ({_human(n)}) — not written or read by any current step')
        if args.apply:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

    if args.dry_run:
        print(f'DONE — dry run: {len(found)} orphan(s), {_human(total)} — pass --apply to remove')
        print('    → run: yoga cache clean --apply')
    else:
        print(f'DONE — removed {len(found)} orphan(s), {_human(total)} freed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
