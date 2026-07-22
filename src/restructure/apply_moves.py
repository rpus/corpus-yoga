#!/usr/bin/env python3
"""
apply_moves.py — execute a room's moves.csv against its real roots.

    python3 apply_moves.py --from <old-layout-repo-root> --moves <moves.csv> [--apply]

Dry-run by default: prints the full plan and exits 1 if anything conflicts.
--apply performs it. Every action is one of:

  MOVE      source exists, destination absent — the move happens
  done      source gone, destination present — another room (or an earlier
            run) already did it; absence of work is a signal, not an error
  CONFLICT  both exist — nothing written, loud, exit 1
  MISSING   neither exists — loud, exit 1

Medium-aware, single-mooring: a datum stays on its medium. Every `data` row's
OLD root must be a symlink; the medium root is recovered from its target (a
DANGLING link still names the medium — in any room applying after the first,
the first room's apply already moved the data on the shared medium, so the
old moorings dangle and their rows read `done`). All rows must agree on ONE
medium root M; the shared-medium move is `M/<old> → M/data/<old>` row by row
(the first room performs it; later rooms find it done). Locally the room then
replaces its old moorings with ONE `data` link to `M/data`, moves its `local`
rows (cache/, logs/ → tmp/) on plain disk, and re-hangs the mount under ext/.

Old roots are removed only when empty; residue is reported, never destroyed.
"""
import argparse
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from common import read_moves


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
            conflicts.append(f'CONFLICT {rule}: both exist: {src} AND {dst}')
        else:
            missing.append(f'MISSING {rule}: neither exists: {src} NOR {dst}')

    # the ONE medium root, recovered from every data mooring's link target
    mediums = {}
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
            conflicts.append(f'ODD-MOORING {old}: link target {target} does not end '
                             f'with {old} — medium root unrecoverable; decide by hand')
            continue
        mediums[old] = target.parents[len(parts) - 1]
    if len(set(mediums.values())) > 1:
        conflicts.append(f'SPLIT-MEDIUM: data moorings disagree on the medium root: '
                         f'{sorted(set(map(str, mediums.values())))}')
    M = next(iter(mediums.values()), None)

    # shared-medium moves (first room performs; later rooms find them done)
    if M:
        for old, new in data_rows:
            plan(M / old, M / new, 'data')
    # the local share: tmp/ lifts and the ext/ mount re-hang
    for old, new, rule in rows:
        if rule == 'local':
            plan(repo / old, repo / new, rule)
        elif rule == 'mount':
            src = repo / old
            dst = repo / new
            target = Path(os.readlink(src)) if src.is_symlink() else None
            plan(src, dst, rule)
            if target is not None:
                links.append((dst, target))
    # the single mooring: data → M/data
    if M:
        mooring = repo / 'data'
        if mooring.is_symlink() or mooring.exists():
            done['mooring'] += 1
        else:
            links.append((mooring, M / 'data'))

    # report the plan
    by_rule = Counter(r for _, _, r in actions)
    print(f'{len(actions)} move(s) to perform:', dict(by_rule) or 'none')
    if done:
        print('already done (skipped):', dict(done))
    for line in conflicts + missing:
        print(f'  {line}')
    for link, target in links:
        print(f'  LINK {link.relative_to(repo)} -> {target}')
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
    old_mount = repo / rows[[r for _, _, r in rows].index('mount')][0] \
        if any(r == 'mount' for _, _, r in rows) else None
    if old_mount is not None and old_mount.is_symlink():
        old_mount.unlink()
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
    if M and (M / 'input').is_dir():
        ds = M / 'input' / '.DS_Store'
        if ds.exists() and sum(1 for _ in (M / 'input').iterdir()) == 1:
            ds.unlink()
        if not any((M / 'input').iterdir()):
            (M / 'input').rmdir()
        else:
            leftovers.append(M / 'input')
    print(f'applied: {len(actions)} move(s), {len(links)} link(s)')
    for l in leftovers:
        print(f'  residue left (inspect by hand): {l}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
