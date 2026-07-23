#!/usr/bin/env python3
"""
compare_outputs.py — is the worktree's rebuilt data/output/ EQUIVALENT to the
room's real output/?

    python3 compare_outputs.py --from <old-layout-repo-root> [--worktree <dir>]

1. markdown equivalence. The map is IDENTITY this service (only the roots
   move), so the bar is byte-identical, full stop: every real file at the
   same relative path, same bytes. Residual differences are findings, not
   allowances.
2. Seeded-tier stability: the precious tiers copied in by build_harness must
   be untouched by the run — any diff means a pipeline wrote where it
   should not.

Exit 0 iff both hold and nothing unexplained appeared.
"""
import argparse
import sys
from pathlib import Path

from common import MARKDOWN_MAP

PRECIOUS = ('artifacts', 'dashboard', 'indexing', 'memories', 'serve_markdown')


def map_path(rel):
    for old, new in MARKDOWN_MAP:
        if rel.startswith(old):
            return new + rel[len(old):]
    return rel


def files(root: Path):
    return {str(p.relative_to(root)): p for p in root.rglob('*')
            if p.is_file() and p.name != '.DS_Store'} if root.is_dir() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='repo', required=True)
    ap.add_argument('--worktree', default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()
    repo, wt = Path(args.repo).resolve(), Path(args.worktree).resolve()

    identical = 0
    findings = []
    real = files(repo / 'output' / 'markdown')
    new = files(wt / 'data' / 'output' / 'markdown')
    claimed = set()
    for rel, p in sorted(real.items()):
        target = map_path(rel)
        claimed.add(target)
        q = new.get(target)
        if q is None:
            findings.append(f'MISSING  {target}')
            continue
        if p.read_bytes() == q.read_bytes():
            identical += 1
        else:
            findings.append(f'DIFFERS  {target}')
    for rel in sorted(set(new) - claimed):
        findings.append(f'EXTRA    {rel}  (no real counterpart)')
    print(f'markdown: {identical} byte-identical, '
          f'{sum(f.startswith("DIFFERS") for f in findings)} differ, '
          f'{sum(f.startswith("MISSING") for f in findings)} missing, '
          f'{sum(f.startswith("EXTRA") for f in findings)} extra')

    for tier in PRECIOUS:
        r, w = files(repo / 'output' / tier), files(wt / 'data' / 'output' / tier)
        changed = [k for k in r if k in w and r[k].read_bytes() != w[k].read_bytes()]
        gone, born = sorted(set(r) - set(w)), sorted(set(w) - set(r))
        findings += [f'MUTATED  data/output/{tier}/{k}' for k in changed]
        findings += [f'DELETED  data/output/{tier}/{k}' for k in gone]
        findings += [f'CREATED  data/output/{tier}/{k}' for k in born]
        print(f'{tier}: ' + ('stable' if not (changed or gone or born) else
                             f'{len(changed)} mutated, {len(gone)} deleted, {len(born)} created'))

    if findings:
        print(f'\n{len(findings)} finding(s):')
        for f in findings[:40]:
            print(f'  {f}')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
