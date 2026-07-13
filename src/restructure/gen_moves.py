#!/usr/bin/env python3
"""
gen_moves.py — scan a room's OLD-layout data roots and emit its move manifest.

    python3 gen_moves.py --from <old-layout-repo-root> [--swap tmp/restructure]

Emits under --swap:
  moves.csv   the ONE authority: old,new,rule — total over the scanned roots
              (every file claimed by exactly one row, or named excluded)
  view/       the manifest rendered as a symlink tree (browse the future;
              nothing real moves). input/ rows under view/input/,
              output/markdown rows under view/output-markdown/, disposals
              under view/disposed/.

Absent roots are skipped with a notice (a room's data holdings are choices);
unrecognized files become UNCLASSIFIED rows and fail the totality check —
a room-local wrinkle surfacing is this tool working, not failing.
Re-runnable: view/ is rebuilt from scratch (L1: re-running is silence).
"""
import argparse
import shutil
import sys
from collections import Counter
from pathlib import Path

from common import MARKDOWN_MAP, write_moves


def scan(repo: Path):
    rows = []
    IN, OMD = repo / 'input', repo / 'output' / 'markdown'

    def claim(old: Path, new_rel: str, rule: str):
        rows.append((str(old.relative_to(repo)), new_rel, rule))

    def absent(root: Path):
        if not root.is_dir():
            print(f'  (no {root.relative_to(repo)} — skipped; optional by room choice)')
            return True
        return False

    # input/browser-captures/claude — split per capture mechanism
    croot = IN / 'browser-captures' / 'claude'
    if not absent(croot):
        for d in sorted(croot.iterdir()):
            if d.name == '.DS_Store':
                continue
            if not d.is_dir():
                claim(d, f'UNCLASSIFIED/{d.name}', 'UNCLASSIFIED')
                continue
            for f in sorted(d.iterdir()):
                if f.name == '.DS_Store':
                    continue
                if f.suffix == '.json':
                    claim(f, f'input/claude/chat/browser-API/{d.name}/{f.name}', 'api-json')
                elif f.suffix == '.md':
                    claim(f, f'input/claude/chat/browser-DOM/{d.name}/{f.name}', 'dom-md')
                elif f.suffix == '.log':
                    claim(f, f'claude/{f.name}', 'dispose')
                else:
                    claim(f, f'UNCLASSIFIED/{d.name}/{f.name}', 'UNCLASSIFIED')

    # input/browser-captures/gemini
    groot = IN / 'browser-captures' / 'gemini'
    if not absent(groot):
        for d in sorted(groot.iterdir()):
            if d.name == '.DS_Store':
                continue
            if d.name == 'ordering.txt':
                claim(d, 'input/gemini/chat/browser-DOM/ordering.txt', 'ordering-capture')
                continue
            if not d.is_dir():
                claim(d, f'UNCLASSIFIED/{d.name}', 'UNCLASSIFIED')
                continue
            for f in sorted(d.iterdir()):
                if f.name == '.DS_Store':
                    continue
                if f.suffix == '.md':
                    claim(f, f'input/gemini/chat/browser-DOM/{d.name}/{f.name}', 'dom-md')
                elif f.suffix == '.log':
                    claim(f, f'gemini/{f.name}', 'dispose')
                else:
                    claim(f, f'UNCLASSIFIED/{d.name}/{f.name}', 'UNCLASSIFIED')

    # input/chat-exports — bulk exports, dir-wise
    xroot = IN / 'chat-exports'
    if not absent(xroot):
        for d in sorted(xroot.iterdir()):
            if d.name == '.DS_Store':
                continue
            if d.is_dir() and d.name.startswith('data-'):
                claim(d, f'input/claude/chat/bulk-export/{d.name}', 'bulk-export')
            else:
                claim(d, f'UNCLASSIFIED/{d.name}', 'UNCLASSIFIED')

    # input/code-agents — the store, room-wise
    aroot = IN / 'code-agents'
    if not absent(aroot):
        for d in sorted(aroot.iterdir()):
            if d.name == '.DS_Store':
                continue
            if d.is_dir():
                claim(d, f'input/claude/code/machine-transport/{d.name}', 'machine-transport')
            else:
                claim(d, f'UNCLASSIFIED/{d.name}', 'UNCLASSIFIED')

    # the live source: renamed, still outside the type tree
    if (IN / 'code-projects').exists():
        rows.append(('input/code-projects', 'input/claude-code-projects',
                     'live-source-rename'))

    # output/markdown — unfuse provider×channel
    for old_prefix, new_prefix in MARKDOWN_MAP:
        p = OMD / old_prefix.rstrip('/')
        if p.is_dir():
            rows.append((f'output/markdown/{old_prefix.rstrip("/")}',
                         f'output/markdown/{new_prefix.rstrip("/")}', 'markdown-channel'))
    rows.append(('output/markdown/index.md', '', 'excluded: cross-corpus index, stays at the root'))
    return rows


def render_view(repo: Path, swap: Path, rows):
    view = swap / 'view'
    if view.exists():
        shutil.rmtree(view)
    for old, new, rule in rows:
        if rule.startswith('excluded') or not new:
            continue
        if rule == 'dispose':
            dst = view / 'disposed' / new
        elif new.startswith('output/markdown/'):
            dst = view / 'output-markdown' / new[len('output/markdown/'):]
        else:
            dst = view / new
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to((repo / old).resolve())


def check_totality(repo: Path, rows):
    claimed_dirs = {o for o, n, r in rows if n and (repo / o).is_dir()}
    claimed_files = {o for o, n, r in rows if n and not (repo / o).is_dir()}
    problems = []
    IN = repo / 'input'
    for p in sorted(IN.rglob('*')) if IN.is_dir() else []:
        if p.name == '.DS_Store' or p.is_dir() or not (p.is_file() or p.is_symlink()):
            continue
        rel = str(p.relative_to(repo))
        if rel.startswith('input/code-projects'):
            continue
        hits = (rel in claimed_files) + any(rel.startswith(d + '/') for d in claimed_dirs)
        if hits != 1:
            problems.append(f'{"UNCLAIMED" if hits == 0 else "DOUBLE"} {rel}')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='repo', required=True,
                    help='the OLD-layout repo root whose data is scanned')
    ap.add_argument('--swap', default='tmp/restructure',
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
    bad = problems or counts.get('UNCLASSIFIED')
    print('totality: OK — every file claimed exactly once' if not bad
          else f'totality: {len(problems)} problem(s), {counts.get("UNCLASSIFIED", 0)} unclassified — '
               'this room has wrinkles the rules do not know; extend or exclude BY HAND')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
