#!/usr/bin/env python
"""
compare_markdown.py — Diff two saved sets of markdown, per conversation, pairing by filename:
  --api     the api-sourced markdown (project_markdown's output, rendered from apiConversation JSON)
  --scrape  the legacy DOM-scrape markdown (<id>/<title>.md under a captures dir)

Pure markdown-vs-markdown: it reads the two directories and compares the files. It does NOT
project anything itself (project_markdown already wrote the api side). The safety net for retiring
the DOM scrape: while both sets exist, this proves the api projection reproduces (or improves on)
what the scrape produced.

Gate on turn structure (machine-robust); content always differs in intended ways (better titles,
trimmed leading spaces, separated run-on blocks) — use --diff to eyeball content, not to gate:
  REGRESSION = api md has FEWER turns than the scrape (dropped content), OR
               MORE turns without the scrape carrying a [no capture] placeholder (spurious turns).
  fine       = equal turns, or more-when-the-scrape-failed (the projection filled the gap).

Usage:
  src/run_python_script.sh src/main/browser-captures/compare_markdown.py \
    --api gen/browser-captures/markdown --scrape ext/browser-captures/claude [--diff]

Exit status is non-zero iff a regression is found (suitable for pipeline gating).
"""
import argparse
import difflib
import re
import sys
from pathlib import Path


def turns(md):
    return (len(re.findall(r'^## Human ', md, flags=re.M)),
            len(re.findall(r'^## (?:Claude|Gemini) ', md, flags=re.M)))


def conv_id(md):
    """The conversation id, from the <url> line both renderers emit (last path segment).
    Robust pairing key -- the two sides slugify different titles, so filenames can diverge."""
    m = re.search(r'<(https?://[^>]+)>', md)
    if not m:
        return None
    return m.group(1).split('?')[0].split('#')[0].rstrip('/').rsplit('/', 1)[-1]


def _index(paths):
    out = {}
    for f in paths:
        text = f.read_text()
        cid = conv_id(text)
        if cid:
            out[cid] = text
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--api', required=True,
                    help='dir of api-sourced <title>.md (project_markdown output)')
    ap.add_argument('--scrape', required=True,
                    help='captures dir of <id>/<title>.md DOM scrapes')
    ap.add_argument('--diff', action='store_true', help='print full per-conversation unified diffs')
    args = ap.parse_args()

    api_md = _index(Path(args.api).glob('*.md'))
    scrape_md = _index(Path(args.scrape).glob('*/*.md'))

    exact = improved = 0
    regressions = []
    paired = sorted(set(api_md) & set(scrape_md))
    for name in paired:
        a = api_md[name]
        s = scrape_md[name]
        ta, ts = turns(a), turns(s)
        has_placeholder = '[no capture' in s
        if ta == ts:
            exact += 1
        elif ta > ts and has_placeholder:
            improved += 1
        else:
            kind = 'dropped turns' if ta < ts else 'spurious turns (no scrape placeholder)'
            regressions.append((name, ts, ta, kind))
        if args.diff:
            print(f"===== {name} =====")
            print('\n'.join(difflib.unified_diff(s.splitlines(), a.splitlines(),
                                                 'scraped', 'api', lineterm='')))

    api_only = sorted(set(api_md) - set(scrape_md))
    scrape_only = sorted(set(scrape_md) - set(api_md))
    print(f"compared {len(paired)}: {exact} turn-exact, {improved} api-more-complete "
          f"(filled scrape gaps), {len(regressions)} regression(s)")
    if api_only:
        print(f"  {len(api_only)} api md(s) with no scrape counterpart (not compared)", file=sys.stderr)
    if scrape_only:
        print(f"  {len(scrape_only)} scrape md(s) with no api counterpart (not compared)", file=sys.stderr)
    for name, ts, ta, kind in regressions:
        print(f"  REGRESSION {name}: scrape {ts} vs api {ta} — {kind}", file=sys.stderr)
    return 1 if regressions else 0


if __name__ == '__main__':
    sys.exit(main())
