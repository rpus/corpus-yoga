#!/usr/bin/env python3
"""
gen_moves.py — scan a room's OLD-layout roots and emit its move manifest.

    python3 gen_moves.py --from <old-layout-repo-root> [--swap swap]

Emits under --swap:
  moves.csv   the ONE authority: old,new,rule — total over the room's roots
              (every root entry claimed by exactly one row, or named excluded)
  view/       the manifest rendered as a symlink tree (browse the future;
              nothing real moves)

Second service: claims are WHOLE-ROOT (the corpus content does not move, only
the roots above it), so the grain is a top-level entry, not a file. Rules:

  mount     input/claude-code-projects → ext/ — a live SOURCE, not a capture
  data      an input/ mooring or the output root → under data/ (moves on its
            medium; apply is medium-aware)
  local     cache/ or logs/ → under tmp/ (plain local move)
  excluded: git-tracked machinery (RUNME.sh, PREREQUISITES.sh) — moves with
            the BRANCH (git mv, already on it), never with apply

Absent roots are skipped with a notice (a room's holdings are choices); a
root entry the rules do not know fails the totality check — a room-local
wrinkle surfacing is this tool working, not failing.
Re-runnable: view/ is rebuilt from scratch (L1: re-running is silence).
"""
import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

from common import ROOT_MAP, SCRIPT_MOVES, write_moves

# root entries that are NOT claimed by any move row: the machinery that stays,
# plus the NEW roots themselves — a mid-transition room legitimately holds
# both layouts (the branch checkout's own gate runs birth tmp/ before apply),
# and the new roots are move TARGETS, never sources (found 2026-07-22,
# home-room: gen_moves flagged the gate-born tmp/ as UNCLAIMED)
MACHINERY = {'.git', '.gitignore', '.DS_Store', 'README.md', 'yoga',
             'src', 'rsc', 'machine-name.txt', 'swap', 'data', 'tmp', 'ext'}


def scan(repo: Path):
    rows = []
    mount_old, mount_new = ROOT_MAP[0]

    def absent(root: Path):
        if not (root.is_dir() or root.is_symlink()):
            print(f'  (no {root.relative_to(repo)} — skipped; optional by room choice)')
            return True
        return False

    # input/ splits per entry: the mount is extracted, the rest lift to data/
    IN = repo / 'input'
    if not absent(IN):
        for d in sorted(IN.iterdir()):
            if d.name == '.DS_Store':
                continue
            rel = f'input/{d.name}'
            if rel == mount_old:
                rows.append((rel, mount_new, 'mount'))
            else:
                rows.append((rel, f'data/input/{d.name}', 'data'))

    # the other three roots lift whole
    for old, new, rule in (('output', 'data/output', 'data'),
                           ('cache', 'tmp/cache', 'local'),
                           ('logs', 'tmp/logs', 'local')):
        if not absent(repo / old):
            rows.append((old, new, rule))

    # the script moves: on the record, off apply's plate (git already did them)
    for old, new in SCRIPT_MOVES:
        rows.append((old, new,
                     'excluded: git-tracked — moves with the branch, not with apply'))
    return rows


def render_view(repo: Path, swap: Path, rows):
    view = swap / 'view'
    if view.exists():
        shutil.rmtree(view)
    for old, new, rule in rows:
        if rule.startswith('excluded') or not new:
            continue
        dst = view / new
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to((repo / old).resolve())


def check_totality(repo: Path, rows):
    """Every root entry is machinery, a script row, or claimed by exactly one row."""
    claimed = Counter(o for o, n, r in rows)
    problems = []
    for p in sorted(repo.iterdir()):
        if p.name in MACHINERY or p.name.endswith('.code-workspace'):
            continue
        if p.name == 'input' and p.is_dir():
            for d in sorted(p.iterdir()):
                if d.name == '.DS_Store':
                    continue
                hits = claimed.get(f'input/{d.name}', 0)
                if hits != 1:
                    problems.append(f'{"UNCLAIMED" if hits == 0 else "DOUBLE"} input/{d.name}')
            continue
        hits = claimed.get(p.name, 0)
        if hits != 1:
            problems.append(f'{"UNCLAIMED" if hits == 0 else "DOUBLE"} {p.name}')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='repo', required=True,
                    help='the OLD-layout repo root whose landscape is scanned')
    ap.add_argument('--swap', default='swap',
                    help='where moves.csv and view/ land (relative to cwd)')
    args = ap.parse_args()

    repo, swap = Path(args.repo).resolve(), Path(args.swap).resolve()
    rows = scan(repo)
    write_moves(swap / 'moves.csv', rows)
    render_view(repo, swap, rows)
    problems = check_totality(repo, rows)

    counts = Counter(r.split(':')[0] for _, _, r in rows)
    print('rule counts:')
    for rule, n in sorted(counts.items()):
        print(f'  {rule:20} {n}')
    print(f'manifest: {swap / "moves.csv"}   view: {swap / "view"}')
    for p in problems[:20]:
        print(f'  {p}')
    print('totality: OK — every root entry claimed exactly once' if not problems
          else f'totality: {len(problems)} problem(s) — this room has entries the '
               'rules do not know; extend or exclude BY HAND')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
