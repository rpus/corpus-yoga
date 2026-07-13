#!/usr/bin/env python3
"""
build_harness.py — materialize dry-run data roots in THIS checkout (the branch
worktree) from a room's moves.csv and its real OLD-layout roots.

    python3 build_harness.py --from <old-layout-repo-root> --moves <moves.csv>

  input/   new-style symlink tree straight from the manifest — the pipelines
           read the future layout, the bytes stay where they are
  cache/   empty — the run must rebuild every derivation (fresh-clone proof)
  output/  precious tiers COPIED in (artifacts, dashboard, indexing, memories,
           serve_markdown, and the summary DEPOSITS path-mapped — deposits,
           not dressing); markdown/ otherwise empty for the rebuild
  the room self-binding under rsc/machines/ copied — same machine, same room,
           honest binding (its filename stays out of committed text, as
           PREREQUISITES' check_room does: the file is machine-local and never
           committed, so xref would read the joined path as a missing file)

Re-runnable: wipes and rebuilds input/, cache/, output/ here (L1).
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

    for root in ('input', 'cache', 'output'):
        p = WT / root
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)

    n = 0
    for old, new, rule in read_moves(args.moves):
        if not new.startswith('input/') or rule.startswith('excluded'):
            continue
        dst = WT / new
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to((repo / old).resolve())
        n += 1
    print(f'input/: {n} symlink(s) from the manifest')

    (WT / 'cache').mkdir()
    (WT / 'output').mkdir()
    for tier in PRECIOUS:
        src = repo / 'output' / tier
        if src.is_dir():
            shutil.copytree(src, WT / 'output' / tier, symlinks=True)
    summaries = repo / 'output' / 'markdown' / 'claude' / 'summaries'
    if summaries.is_dir():
        dst = WT / 'output' / 'markdown' / 'claude' / 'chat' / 'summaries'
        dst.parent.mkdir(parents=True)
        shutil.copytree(summaries, dst, symlinks=True)
    (WT / 'output' / 'markdown').mkdir(exist_ok=True)
    print('cache/: empty; output/: precious tiers + summary deposits seeded, markdown otherwise empty')

    binding = repo / 'rsc' / 'machines' / 'self.txt'
    if binding.exists():
        shutil.copy(binding, WT / 'rsc' / 'machines' / 'self.txt')
        print('machine binding: copied (same machine, same room)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
