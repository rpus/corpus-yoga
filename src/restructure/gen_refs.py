#!/usr/bin/env python3
"""
gen_refs.py — the code-side manifest of the four-root restructure.

Scans every committed file for references to the OLD root layout and emits
refs.csv (file, line, kind, pattern, proposal, text): the reviewable record of
what the code sweep must touch. Kinds:

  mechanical — an unambiguous old→new string swap (REF_MAP in common.py;
               apply_refs.py performs exactly these)
  decide     — a site needing judgment before any swap:
                 * quoted join forms ('input' may be a path segment or a key)
                 * .gitignore anchors (rewritten as a block, not per line)
                 * RUNME.sh / PREREQUISITES.sh invocation forms in prose

The sweep converges: after it is applied, re-running me approaches zero rows
(new forms are excluded by lookaround, e.g. data/input/ no longer matches).
Skipped files (derived, this machinery, format histories, .gitignore) are
declared in common.SWEEP_SKIP_*.
"""
import csv, re, subprocess
from pathlib import Path

from common import REF_MAP, SWEEP_SKIP_FILES, SWEEP_SKIP_PREFIXES

# (name, regex, proposal, kind) — a line may hit several patterns; one row each
P = [(name, rx, new, 'mechanical') for name, rx, new in REF_MAP] + [
    # the observed idiom is single-quoted segments; already-prefixed new forms
    # ('data' / 'input', 'tmp' / 'cache') are excluded so the sweep converges
    ('join-form', r"(?<!'data' / )'(?:input|output)'\s*/|(?<!'tmp' / )'(?:cache|logs)'\s*/"
                  r"|(?<!'data' )/\s*'(?:input|output)'|(?<!'tmp' )/\s*'(?:cache|logs)'",
     "path join: prefix the parent segment ('data' or 'tmp') — but a quoted "
     'tier word may be a KEY, not a path; choose per site', 'decide'),
    ('gitignore-anchor', r'^/(input|output|cache|logs)\b',
     'rewrite the ignore block whole: /data /tmp /ext /swap /machine-name.txt',
     'decide'),
    # `\./` alternative: dot-slash invocations are hits; path-tail forms
    # (src/RUNME.sh, src/main/<pipeline>/RUNME.sh) are legitimately excluded
    ('runme', r'''(?<![\w/])\./RUNME\.sh|(?<![\w/.'"])RUNME\.sh''',
     'src/RUNME.sh (invocation forms vary: ./RUNME.sh, bare, prose)', 'decide'),
    ('prereqs', r'''(?<![\w/])\./PREREQUISITES\.sh|(?<![\w/.'"])PREREQUISITES\.sh''',
     'src/PREREQUISITES.sh (invocation forms vary)', 'decide'),
]


def sweep_files(repo: Path):
    """The committed files the sweep may touch — shared with apply_refs.py."""
    return [f for f in subprocess.run(['git', 'ls-files'], cwd=repo, capture_output=True,
                                      text=True).stdout.split()
            if f not in SWEEP_SKIP_FILES
            and not any(f.startswith(p) for p in SWEEP_SKIP_PREFIXES)]


if __name__ == '__main__':
    import argparse
    _ap = argparse.ArgumentParser()
    _ap.add_argument('--from', dest='repo', required=True,
                     help='the checkout whose committed files are scanned')
    # refs.csv lands under the swap space, NEVER the cwd: a refs.csv at the
    # repo root is not gitignored, and the next `yoga check` scans it — its
    # migration-path rows read as hundreds of missing-file references and
    # rewrite xref.csv into a failing state (found 2026-07-23 by reading-room,
    # whose main a cwd-written refs.csv corrupted).
    _ap.add_argument('--swap', default='swap',
                     help='where refs.csv lands (relative to cwd; gitignored)')
    _args = _ap.parse_args()
    REPO = Path(_args.repo).resolve()
    OUT = Path(_args.swap).resolve() / 'refs.csv'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for rel in sweep_files(REPO):
        p = REPO / rel
        try:
            text = p.read_text()
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, rx, proposal, kind in P:
                if re.search(rx, line):
                    rows.append((rel, lineno, kind, name, proposal, line.strip()[:160]))

    with open(OUT, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['file', 'line', 'kind', 'pattern', 'proposal', 'text'])
        w.writerows(rows)

    from collections import Counter
    by_kind = Counter(r[2] for r in rows)
    by_file = Counter(r[0] for r in rows)
    print(f'{len(rows)} reference(s) across {len(by_file)} file(s)')
    print('by kind:', dict(by_kind))
    print('\ntop files:')
    for f, n in by_file.most_common(12):
        print(f'  {n:4} {f}')
    print('\ndecide sites by pattern:')
    for pat, n in Counter(r[3] for r in rows if r[2] == 'decide').most_common():
        print(f'  {n:4} {pat}')
