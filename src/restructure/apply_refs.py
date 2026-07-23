#!/usr/bin/env python3
"""
apply_refs.py — perform the MECHANICAL half of the code-side sweep.

    python3 apply_refs.py --from <branch-checkout> [--apply]

Applies exactly common.REF_MAP (the same regexes gen_refs.py reports as
`mechanical`) to every sweep-eligible committed file, in place. Dry-run by
default: prints per-file substitution counts and changes nothing. The
`decide` sites (join forms, .gitignore block, script invocation prose) are
NOT touched — those are judgment, made by hand and reviewed in the diff.

Idempotent: the lookarounds exclude the new forms, so a second run is silence.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from common import REF_MAP
from gen_refs import sweep_files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='repo', required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    total = Counter()
    touched = 0
    for rel in sweep_files(repo):
        p = repo / rel
        try:
            text = p.read_text()
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        new_text, counts = text, Counter()
        for name, rx, new in REF_MAP:
            new_text, n = re.subn(rx, new, new_text)
            if n:
                counts[name] += n
        if not counts:
            continue
        touched += 1
        total.update(counts)
        print(f'  {sum(counts.values()):4}  {rel}  {dict(counts)}')
        if args.apply:
            p.write_text(new_text)

    print(f'{sum(total.values())} substitution(s) in {touched} file(s):', dict(total))
    print('applied' if args.apply else 'dry run (pass --apply to perform)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
