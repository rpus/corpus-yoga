#!/usr/bin/env python
"""
compare_markdown.py — Verify the markdownConversation projection reproduces (or improves on)
the legacy DOM scrape, per conversation. The safety net for retiring browser-chat-capture.js:
while both artifacts exist, this proves every conversation projects faithfully.

It pairs by capture dir (uuid) and compares turn structure (and, with --diff, full text):

  REGRESSION  = projection has FEWER turns than the scrape (dropped content), OR
                MORE turns without the scrape carrying a [no capture] placeholder
                (spurious turns, e.g. dead edited/regenerated branches).
  fine        = equal turns, or more-turns-when-the-scrape-failed (projection fills the gap).

Turn structure is the machine-robust invariant to gate on; content always differs in
intended ways (better titles, trimmed leading spaces, separated run-on blocks), so use
--diff to eyeball content divergences rather than gating on them.

Usage:
  src/run_python_script.sh src/main/browser-captures/compare_markdown.py \
    --browser-captures ext/browser-captures/claude [--diff]

Exit status is non-zero iff a regression is found (suitable for pre_commit).
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

from project_markdown import project, render, find_api_json


def turns(md):
    return (len(re.findall(r'^## Human ', md, flags=re.M)),
            len(re.findall(r'^## Claude ', md, flags=re.M)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', required=True, help='dir of <uuid>/ capture folders')
    ap.add_argument('--diff', action='store_true', help='print full per-conversation unified diffs')
    args = ap.parse_args()

    n = exact = improved = 0
    regressions = []
    for d in sorted(p for p in Path(args.browser_captures).iterdir() if p.is_dir()):
        mds = list(d.glob('*.md'))
        api = find_api_json(d)
        if not mds or api is None:
            continue
        n += 1
        scraped = mds[0].read_text()
        projected = render(project(api))
        s, p = turns(scraped), turns(projected)
        has_placeholder = '[no capture' in scraped
        if p == s:
            exact += 1
        elif p > s and has_placeholder:
            improved += 1
        else:
            kind = 'dropped turns' if p < s else 'spurious turns (no scrape placeholder)'
            regressions.append((d.name, s, p, kind))
        if args.diff:
            diff = difflib.unified_diff(scraped.splitlines(), projected.splitlines(),
                                        'scraped', 'projected', lineterm='')
            print(f"===== {d.name} =====")
            print('\n'.join(diff))

    print(f"compared {n}: {exact} turn-exact, {improved} projection-more-complete "
          f"(filled scrape gaps), {len(regressions)} regression(s)")
    for name, s, p, kind in regressions:
        print(f"  REGRESSION {name}: scrape {s} vs projected {p} — {kind}", file=sys.stderr)
    return 1 if regressions else 0


if __name__ == '__main__':
    sys.exit(main())
