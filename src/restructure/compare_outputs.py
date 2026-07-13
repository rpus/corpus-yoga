#!/usr/bin/env python3
"""
compare_outputs.py — is the worktree's rebuilt output/ EQUIVALENT to the room's
real one?

    python3 compare_outputs.py --from <old-layout-repo-root> [--worktree <dir>]

1. output/markdown equivalence, modulo the declared MARKDOWN_MAP. Every real
   file must appear at its mapped path; bytes identical — or identical once
   the map is applied to the real content (embedded corpus links). Residual
   differences are findings, not allowances.
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


def map_content(text):
    for old, new in MARKDOWN_MAP:
        text = text.replace(old, new)
    return text


def files(root: Path):
    return {str(p.relative_to(root)): p for p in root.rglob('*')
            if p.is_file() and p.name != '.DS_Store'} if root.is_dir() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='repo', required=True)
    ap.add_argument('--worktree', default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()
    repo, wt = Path(args.repo).resolve(), Path(args.worktree).resolve()

    identical = mapped = 0
    findings = []
    real, new = files(repo / 'output' / 'markdown'), files(wt / 'output' / 'markdown')
    claimed = set()
    for rel, p in sorted(real.items()):
        target = map_path(rel)
        claimed.add(target)
        q = new.get(target)
        if q is None:
            findings.append(f'MISSING  {target}  (from {rel})')
            continue
        a, b = p.read_bytes(), q.read_bytes()
        if a == b:
            identical += 1
        elif map_content(a.decode('utf-8', 'replace')) == b.decode('utf-8', 'replace'):
            mapped += 1
        else:
            findings.append(f'DIFFERS  {target}  (beyond the path map)')
    for rel in sorted(set(new) - claimed):
        findings.append(f'EXTRA    {rel}  (no real counterpart)')
    print(f'markdown: {identical} byte-identical, {mapped} identical-after-path-map, '
          f'{sum(f.startswith("DIFFERS") for f in findings)} differ, '
          f'{sum(f.startswith("MISSING") for f in findings)} missing, '
          f'{sum(f.startswith("EXTRA") for f in findings)} extra')

    for tier in PRECIOUS:
        r, w = files(repo / 'output' / tier), files(wt / 'output' / tier)
        changed = [k for k in r if k in w and r[k].read_bytes() != w[k].read_bytes()]
        gone, born = sorted(set(r) - set(w)), sorted(set(w) - set(r))
        findings += [f'MUTATED  output/{tier}/{k}' for k in changed]
        findings += [f'DELETED  output/{tier}/{k}' for k in gone]
        findings += [f'CREATED  output/{tier}/{k}' for k in born]
        print(f'{tier}: ' + ('stable' if not (changed or gone or born) else
                             f'{len(changed)} mutated, {len(gone)} deleted, {len(born)} created'))

    if findings:
        print(f'\n{len(findings)} finding(s):')
        for f in findings[:40]:
            print(f'  {f}')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
