#!/usr/bin/env python3
"""
apply_moves.py — execute a room's moves.csv against its real roots.

    python3 apply_moves.py --from <old-layout-repo-root> --moves <moves.csv> [--apply]

Dry-run by default: prints the full plan and exits 1 if anything conflicts.
--apply performs it. NOTHING MOVES ON THE MEDIUM (the PR #20 review's
simplification): the room's old moorings already point into one medium
parent that already contains input/ + output/ — that parent simply IS the
data/ container. So the whole apply is local and additive:

  LINK data -> <medium parent>     derived from this room's own moorings
                                   (they must agree on ONE parent; a datum
                                   is never moved to make that true)
  LINK ext/<mount>                 re-hung at the old mount's own target
  MOVE cache -> tmp/cache          plain local moves (keep the validation
  MOVE logs  -> tmp/logs           memoisation; both dirs stay disposable)
  UNLINK old moorings              input/<provider>, output — subsumed by
                                   data/; the pointed-at bytes are untouched
  retire old roots                 removed only when empty; residue reported

data/ and ext/ are PRE-MOORABLE: a room may create either link before the
code lands (they conflict with nothing), and this tool then reports them
`done`. Local moves keep the five-state lattice — MOVE / done / CONFLICT /
MISSING — loud and refusing on conflict (the gate-born tmp/ is the known
CONFLICT; the recipe's step 5 disposes it first). Paths print ~-shortened:
committed text and records never name a username.
"""
import argparse
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from common import read_moves


def tilde(p) -> str:
    s = str(p)
    home = str(Path.home())
    return '~' + s[len(home):] if s.startswith(home) else s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='repo', required=True)
    ap.add_argument('--moves', required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    rows = read_moves(Path(args.moves).resolve())

    actions, links, conflicts, missing = [], [], [], []
    done = Counter()

    def plan(src: Path, dst: Path, rule: str):
        s, d = src.exists() or src.is_symlink(), dst.exists() or dst.is_symlink()
        if s and not d:
            actions.append((src, dst, rule))
        elif not s and d:
            done[rule] += 1
        elif s and d:
            conflicts.append(f'CONFLICT {rule}: both exist: {tilde(src)} AND {tilde(dst)}')
        else:
            missing.append(f'MISSING {rule}: neither exists: {tilde(src)} NOR {tilde(dst)}')

    # The ONE medium parent, derived from this room's own data moorings — each
    # mooring's link target must sit under a common parent at its own old
    # relative path (input/claude -> P/input/claude, output -> P/output). The
    # moorings must AGREE; nothing is ever moved to make that true.
    parents = {}
    data_rows = [(o, n) for o, n, r in rows if r == 'data']
    for old, new in data_rows:
        p = repo / old
        if not p.is_symlink():
            conflicts.append(f'LOCAL-DATA {old}: not a symlink — data/ is pure medium; '
                             'moor it (or decide by hand) before applying')
            continue
        target = Path(os.readlink(p))
        parts = old.split('/')
        if list(target.parts[-len(parts):]) != parts:
            conflicts.append(f'ODD-MOORING {old}: link target {tilde(target)} does not '
                             f'end with {old} — parent unrecoverable; decide by hand')
            continue
        parents[old] = target.parents[len(parts) - 1]
    if len(set(parents.values())) > 1:
        conflicts.append('SPLIT-MEDIUM: data moorings disagree on the parent: '
                         f'{sorted(tilde(p) for p in set(parents.values()))}')
    P = next(iter(parents.values()), None)

    # every data row must already rest under the parent — verified, never moved
    if P:
        for old, new in data_rows:
            if old in parents and not (P / old).exists():
                missing.append(f'MISSING data: {tilde(P / old)} absent on the medium')
        mooring = repo / 'data'
        if mooring.is_symlink() or mooring.exists():
            done['mooring'] += 1                     # pre-moored — additive, fine
        else:
            links.append((mooring, P))
    # the local share: tmp/ lifts and the ext/ mount re-hang
    for old, new, rule in rows:
        if rule == 'local':
            plan(repo / old, repo / new, rule)
        elif rule == 'mount':
            src, dst = repo / old, repo / new
            target = Path(os.readlink(src)) if src.is_symlink() else None
            plan(src, dst, rule)
            if target is not None:
                links.append((dst, target))

    # report the plan
    by_rule = Counter(r for _, _, r in actions)
    print(f'{len(actions)} move(s) to perform:', dict(by_rule) or 'none',
          '— nothing moves on the medium')
    if done:
        print('already done (skipped):', dict(done))
    for line in conflicts + missing:
        print(f'  {line}')
    for link, target in links:
        print(f'  LINK {link.relative_to(repo)} -> {tilde(target)}')
    for old, _ in data_rows:
        if (repo / old).is_symlink():
            print(f'  UNLINK {old} (old mooring, subsumed by data/)')

    if conflicts or missing:
        print('unresolved rows — nothing applied' if not args.apply
              else 'unresolved rows — REFUSING to apply')
        return 1
    if not args.apply:
        print('dry run (pass --apply to perform)')
        return 0

    for src, dst, rule in actions:
        if rule == 'mount':
            continue                       # re-hung as a link below, not moved
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    for link, target in links:
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.is_symlink() and not link.exists():
            link.symlink_to(target)
    # retire the old moorings and roots: links unlinked, dirs removed ONLY when empty
    leftovers = []
    for old, _ in data_rows:
        p = repo / old
        if p.is_symlink():
            p.unlink()
    for old, _, rule in rows:
        if rule == 'mount' and (repo / old).is_symlink():
            (repo / old).unlink()
    for root in ('input', 'cache', 'logs'):
        p = repo / root
        if p.is_symlink():
            p.unlink()
        elif p.is_dir():
            ds = p / '.DS_Store'
            if ds.exists() and sum(1 for _ in p.iterdir()) == 1:
                ds.unlink()
            if not any(p.iterdir()):
                p.rmdir()
            else:
                leftovers.append(p)
    print(f'applied: {len(actions)} move(s), {len(links)} link(s) — the medium untouched')
    for l in leftovers:
        print(f'  residue left (inspect by hand): {tilde(l)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
