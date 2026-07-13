#!/usr/bin/env python3
"""
apply_moves.py — execute a room's moves.csv against its real data roots.

    python3 apply_moves.py --from <old-layout-repo-root> --moves <moves.csv> [--apply]

Dry-run by default: prints the full plan and exits 1 if anything conflicts.
--apply performs it. Every action is one of:

  MOVE      source exists, destination absent — the move happens
  done      source gone, destination present — another room (or an earlier
            run) already did it; absence of work is a signal, not an error
  CONFLICT  both exist — nothing written, loud, exit 1
  MISSING   neither exists — loud, exit 1

Medium-aware: a datum stays on its medium. The destination of an input/ move
is computed against the base its OLD root resolves to (an iCloud-symlinked
root migrates ON iCloud, shared by every room; a plain local dir migrates
locally). After the data moves, THIS room's symlink boundary is (re)made:
input/<provider> links to each non-local medium base, and
input/claude-code-projects replaces input/code-projects (same target).
Disposals move to <swap>/disposed/ beside the manifest — never deleted here.

Old roots are removed only when empty; residue is reported, never destroyed.
"""
import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

from common import read_moves

DATA_RULES = {'api-json', 'dom-md', 'ordering-capture', 'bulk-export', 'machine-transport'}
OLD_INPUT_ROOTS = ('browser-captures', 'chat-exports', 'code-agents')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='repo', required=True)
    ap.add_argument('--moves', required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    moves_csv = Path(args.moves).resolve()
    swap = moves_csv.parent
    rows = read_moves(moves_csv)

    # each OLD input root's medium base: where its data really lives. In ANY room
    # that applies after the first, this root is a DANGLING symlink — it points at
    # an iCloud path the first room's apply already moved away — so p.exists() is
    # False. resolve() still recovers the (now-absent) target's parent, i.e. the
    # medium base, so key on is_symlink() too; exists() alone strands every data row
    # as MISSING (dest computed against the local input/ instead of iCloud, where
    # the shared data now lives) and refuses. The first room never hit this: its
    # roots still resolved. Boundary links derive from these bases, so they heal too.
    base_of = {}
    for seg in OLD_INPUT_ROOTS:
        p = repo / 'input' / seg
        if p.is_symlink() or p.exists():
            base_of[seg] = p.resolve().parent

    actions, conflicts, missing = [], [], []
    done = Counter()

    def plan(src: Path, dst: Path, rule: str):
        s, d = src.exists() or src.is_symlink(), dst.exists()
        if s and not d:
            actions.append((src, dst, rule))
        elif not s and d:
            done[rule] += 1
        elif s and d:
            conflicts.append(f'CONFLICT {rule}: both exist: {src} AND {dst}')
        else:
            missing.append(f'MISSING {rule}: neither exists: {src} NOR {dst}')

    providers_by_base = {}
    for old, new, rule in rows:
        if rule.startswith('excluded') or rule == 'live-source-rename':
            continue
        src = (repo / old)
        if rule == 'dispose':
            dst = swap / 'disposed' / new
            # A dispose source already gone was disposed by the FIRST room: the shared
            # .log lived on iCloud, and disposal moved the single copy to that room's
            # local swap/disposed/. A subsequent room has nothing to move — done, not
            # MISSING; its own disposed/ was never meant to hold a second copy. (Same
            # first-vs-subsequent asymmetry as the medium base above.)
            if not (src.exists() or src.is_symlink()) and not dst.exists():
                done[rule] += 1
            else:
                plan(src, dst, rule)
            continue
        if rule == 'markdown-channel':
            plan(src, repo / new, rule)
            continue
        if rule in DATA_RULES:
            seg = old.split('/')[1]              # the OLD first segment under input/
            base = base_of.get(seg, repo / 'input')
            rel = new[len('input/'):]
            plan(src, base / rel, rule)
            providers_by_base.setdefault(rel.split('/')[0], set()).add(base)
            continue
        conflicts.append(f'CONFLICT unknown rule {rule!r}: {old}')

    # report the plan
    by_rule = Counter(r for _, _, r in actions)
    print(f'{len(actions)} move(s) to perform:', dict(by_rule) or 'none')
    if done:
        print('already done (skipped):', dict(done))
    for line in conflicts + missing:
        print(f'  {line}')

    # the per-room symlink boundary, stated in the plan
    boundary = []
    for provider, bases in sorted(providers_by_base.items()):
        for base in bases:
            if base != repo / 'input':
                boundary.append((repo / 'input' / provider, base / provider))
    cp = repo / 'input' / 'code-projects'
    if any(r == 'live-source-rename' for _, _, r in rows) and cp.is_symlink():
        boundary.append((repo / 'input' / 'claude-code-projects', Path(str(cp.readlink()))))
    for link, target in boundary:
        print(f'  LINK {link.relative_to(repo)} -> {target}')

    if conflicts or missing:
        print('unresolved rows — nothing applied' if not args.apply
              else 'unresolved rows — REFUSING to apply')
        return 1
    if not args.apply:
        print('dry run (pass --apply to perform)')
        return 0

    for src, dst, rule in actions:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    for link, target in boundary:
        if not link.is_symlink() and not link.exists():
            link.symlink_to(target)
    if cp.is_symlink():
        cp.unlink()

    # retire the old roots: symlinks unlinked, real dirs removed ONLY when empty
    leftovers = []
    for seg in OLD_INPUT_ROOTS:
        p = repo / 'input' / seg
        real = base_of.get(seg)
        if p.is_symlink():
            p.unlink()
        old_real = (real / seg) if real else p
        if old_real.is_dir():
            for d in sorted(old_real.rglob('*'), reverse=True):
                if d.name == '.DS_Store':
                    d.unlink()
                elif d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
            if not any(old_real.iterdir()):
                old_real.rmdir()
            else:
                leftovers.append(old_real)
    # ...and the emptied parents a markdown-channel move leaves behind (the
    # first real apply left output/markdown/code standing over its moved child)
    for old, new, rule in rows:
        if rule != 'markdown-channel':
            continue
        parent = (repo / old).parent
        if parent != repo / 'output' / 'markdown' and parent.is_dir():
            ds = parent / '.DS_Store'
            if ds.exists() and sum(1 for _ in parent.iterdir()) == 1:
                ds.unlink()
            if not any(parent.iterdir()):
                parent.rmdir()
    print(f'applied: {len(actions)} move(s), {len(boundary)} link(s)')
    for l in leftovers:
        print(f'  residue left (inspect by hand): {l}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
