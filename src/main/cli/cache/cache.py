#!/usr/bin/env python
"""
cache.py — the `corpus-yoga cache` dispatcher. `cache` is a NOUN: the rebuildable tmp/cache/
tier. Bare shows its state and writes nothing; the verbs do the work.

    corpus-yoga cache                    # status: the tmp/cache/ subtrees present, each orphan, and what to run next
    corpus-yoga cache clean              # remove the orphaned subtrees the status names (neither written nor read)
    corpus-yoga cache sync [--dry-run]   # rebuild tmp/cache/ by running each registry row's producers

Thin verb router over the sibling implementations — src/main/cli/cache/clean.py and
src/main/cli/cache/sync.py — so the CLI table carries one `cache` command whose verbs
are the two halves of the reproduction ritual: `corpus-yoga cache clean &&
corpus-yoga cache sync` gives a fresh tmp/cache/ from data/input/ + data/output/ alone. `sync` is the
idempotent regenerator (L1); `clean` is the only destructive verb, and takes no flag
(issues/865): what it would remove is what bare cache names under orphans: and now:.
STDLIB-ONLY, like everything it routes to.
"""
import os
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / 'src' / 'main'))  # src/main - the tier's shared modules
import tier  # noqa: E402 — the tiers, one home (issues/702)
import facts  # noqa: E402 - the one printer of a status's facts (issues/753)
import spell  # noqa: E402
sys.path.insert(0, str(HERE))
from cache_io import human, orphans, size_of  # noqa: E402 - the registry, and what it does not own (issues/865)
VERBS = {'clean': 'clean.py', 'sync': 'sync.py'}
USAGE = (__doc__ or '').strip()


@dataclass
class Tree:
    subtrees: list[str] | str


@dataclass
class Orphan:
    """An entry under tmp/cache that no current step writes or reads, with the act that removes it."""
    size: str
    why: str = facts.phrase('no current step writes or reads it')
    remedy: facts.Command = facts.Command(spell.line('cache', 'clean'), facts.phrase('would remove it'))


@dataclass
class Status:
    """Bare corpus-yoga cache: the subtrees present, each orphan by its path, and under
    now: the cleaner over what it would remove, by path (issues/865), so that the room's one
    reading, which folds this block, names an orphaned subtree a room carries."""
    tmp_cache: Tree = facts.named('tmp/cache')
    orphans: dict[str, Orphan] | None = None
    cache: str = ''               # the tree's count, a fact of the room; a status ends on now: (issues/740)
    now: dict[str, dict[str, dict[str, int]]] | str | None = None


def status_facts() -> Status:
    """The bare-noun default as facts: the state, nothing written."""
    cache = tier.TMP / 'cache'
    subs = sorted(p.name for p in cache.iterdir() if p.is_dir()) if cache.is_dir() else []
    found = {p.relative_to(REPO).as_posix(): Orphan(human(size_of(p))) for p in orphans(cache)}
    return Status(Tree(subs or 'none'), found,
                  facts.phrase('{n} subtree(s) present, {orphans} orphan(s)', n=len(subs), orphans=len(found)) if found
                  else facts.phrase('{n} subtree(s) present', n=len(subs)),
                  {spell.line('cache', 'clean'): {'would remove': {rel: 1 for rel in found}}} if found else facts.phrase('none - nothing to do'))


def status() -> int:
    facts.say(status_facts())
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
        print('error: ' + facts.phrase('{verb} is no verb it takes - {verbs} (bare is the status; corpus-yoga cache <verb> -h says its flags)', verb=repr(verb), verbs=' | '.join(VERBS)), file=sys.stderr)
        return 1
    # execv replaces the process — the verb's own exit status is the exit status
    os.execv(sys.executable, [sys.executable, str(HERE / target), *sys.argv[2:]])


if __name__ == '__main__':
    raise SystemExit(main())
