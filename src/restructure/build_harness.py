#!/usr/bin/env python3
"""
build_harness.py — materialize dry-run roots in THIS checkout (the branch
worktree) from a room's moves.csv and its real OLD-layout roots.

    python3 build_harness.py --from <old-layout-repo-root> --moves <moves.csv>

  data/input/  new-style symlink tree straight from the manifest — the
               pipelines read the future layout, the bytes stay where they are
  tmp/         empty cache/ + logs/ — the run must rebuild every derivation
               (fresh-clone proof)
  data/output/ precious tiers COPIED in (artifacts, dashboard, indexing,
               memories, serve_markdown) plus the summary DEPOSITS at their
               unchanged corpus path (identity map this service — deposits,
               not dressing); markdown/ otherwise empty for the rebuild
  ext/         the mount re-hung, pointing at the REAL foreign store —
               readable in rehearsal; capture stays untested here (it would
               write the real store)
  machine-name.txt copied — same machine, same room, honest binding

Re-runnable: wipes and rebuilds data/, tmp/, ext/ here (L1).
"""
import argparse
import shutil
import sys
from pathlib import Path

from common import read_moves

WT = Path(__file__).resolve().parents[2]
PRECIOUS = ('artifacts', 'dashboard', 'indexing', 'memories', 'serve_markdown')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='repo', required=True)
    ap.add_argument('--moves', required=True)
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    assert (WT / '.git').exists() and WT != repo, f'run me from a worktree checkout, not {repo}'

    for root in ('data', 'tmp', 'ext'):
        p = WT / root
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)

    n = 0
    for old, new, rule in read_moves(args.moves):
        if rule == 'mount':
            dst = WT / new
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to((repo / old).resolve())
            print(f'ext/: {new} -> the real store (read in rehearsal, capture untested)')
        elif new.startswith('data/input/'):
            dst = WT / new
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to((repo / old).resolve())
            n += 1
    print(f'data/input/: {n} symlink(s) from the manifest')

    (WT / 'tmp' / 'cache').mkdir(parents=True)
    (WT / 'tmp' / 'logs').mkdir()
    (WT / 'data' / 'output').mkdir(parents=True)
    for tier in PRECIOUS:
        src = repo / 'output' / tier
        if src.is_dir():
            shutil.copytree(src, WT / 'data' / 'output' / tier, symlinks=True)
    summaries = repo / 'output' / 'markdown' / 'claude' / 'chat' / 'summaries'
    if summaries.is_dir():
        dst = WT / 'data' / 'output' / 'markdown' / 'claude' / 'chat' / 'summaries'
        dst.parent.mkdir(parents=True)
        shutil.copytree(summaries, dst, symlinks=True)
    (WT / 'data' / 'output' / 'markdown').mkdir(exist_ok=True)
    print('tmp/: empty; data/output/: precious tiers + summary deposits seeded, '
          'markdown otherwise empty')

    binding = repo / 'machine-name.txt'
    if binding.exists():
        shutil.copy(binding, WT / 'machine-name.txt')
        print('machine binding: copied (same machine, same room)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
