#!/usr/bin/env python
"""
clean.py - remove the ORPHANED tmp/cache/ entries bare corpus-yoga cache names: paths the
machinery neither writes nor reads (src/main/cli/cache/cache_io.py `orphans`).

tmp/cache/ is the workshop - rebuildable derivations, every live subtree OWNED by a
pipeline (its validation/derivation tree) or an out-of-band command (its output). A path
under tmp/cache/ that is neither an owned subtree, nor inside one, nor an ancestor of one
(a parent kept only to reach owned children) is RESIDUE: a former output whose producer
moved or was renamed - the completion home before pull/785, tmp/cache/completions, is the
latest case. Being derived, an orphan is safe to remove (nothing regenerates it here); and
even a mistaken removal of a LIVE subtree costs only a pipeline re-run, never data - that
is the tmp/cache/ contract (rsc/CALCULUS.md, the 'derived' class: always rebuildable).

The owned-set is DECLARED in rsc/cache_io.csv (via cache_io.py), shared with sync and
`corpus-yoga test run`'s check_cache_io - one registry, three consumers.

The verb takes no flag (issues/865), as the stage's and the store's cleaners do (issues/844): what it
would remove is what the status names, and its faces are src/main/cleaner.py's - will
remove: before each act, did or did NOT after, next: and the verdict last (issues/801).

Usage:
    corpus-yoga cache clean
"""
import shutil
import sys
from pathlib import Path

SELF = 'src/main/cli/cache/clean.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main'))  # src/main - the tier's shared modules
import cleaner  # noqa: E402 - the one loop every clean verb runs (issues/837)
import facts  # noqa: E402
import tier  # noqa: E402 — the tiers, one home (issues/702)
sys.path.insert(0, str(REPO_ROOT / 'src'))  # src/ — modules both tiers import
from declared_parser import verb_parser  # noqa: E402
sys.path.insert(0, str(_file.parent))
import cache as noun  # noqa: E402 - the status the cleaner relays
from cache_io import human, orphans, size_of  # noqa: E402

REPO = REPO_ROOT
CACHE = tier.TMP / 'cache'
KINDS = {'orphan': 'orphans'}


def _dispose(path: Path) -> str | None:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
    except OSError as e:
        return (e.strerror or str(e)).lower()
    return None if not (path.exists() or path.is_symlink()) else 'still present'


def entries() -> list[cleaner.Entry]:
    """Everything the janitor acts on: each orphan by its path, with its size."""
    return [cleaner.Entry('orphan', p.relative_to(REPO).as_posix(),
                          {'orphan': 'no current step writes or reads it', 'size': human(size_of(p))},
                          lambda p=p: _dispose(p), p.relative_to(REPO).as_posix())
            for p in orphans(CACHE)]


def main() -> int:
    verb_parser('cache', 'clean').parse_args()
    return cleaner.clean('cache', entries(), KINDS, lambda: own if isinstance(own := noun.status_facts().next, dict) else {})


if __name__ == '__main__':
    sys.exit(main())
