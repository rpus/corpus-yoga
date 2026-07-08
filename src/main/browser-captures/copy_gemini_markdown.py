#!/usr/bin/env python
"""
copy_gemini_markdown.py — copy gemini scrape markdown into the presentation tree
(lib/markdown/gemini/conversations, beside claude's projections), anchoring each turn heading:

    ## Human (3)   ->   ## Human (3) <a id="human-3"></a>

Gemini has no API and so no message uuids; the role-count anchor is the best turn
identity available, and gemini conversations are append-only (the audit tail-probe
already relies on this), so an anchor never moves — later captures only add turns.
Anchors ride the heading line, where compare_markdown.turn_seq's `## <Role> [^\\n]*`
split ignores them. The ext/ scrapes themselves are data and are left untouched;
this derived copy is the navigable/indexable surface.

A filename collision between conversations gets the conversation id prefixed
(same rule as before this script replaced the RUNME.sh copy loop).

Usage:
  src/run_python_script.sh src/main/browser-captures/copy_gemini_markdown.py \
    [--browser-captures ext/browser-captures/gemini] [--out gen/markdown/gemini]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import REPO, MD033_PRAGMA, reconcile_dir

HEADING = re.compile(r'^## (Human|Gemini) \((\d+)\)$', flags=re.M)


def anchored(md):
    md = HEADING.sub(lambda m: f'## {m[1]} ({m[2]}) <a id="{m[1].lower()}-{m[2]}"></a>', md)
    # same lint pragma as render() emits, inserted after the title line (the scrapes in
    # ext/ stay pristine; only this derived copy carries presentation dressing)
    first, _, rest = md.partition('\n')
    return f'{first}\n\n{MD033_PRAGMA}\n\n{rest.lstrip()}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-captures', default=str(REPO / 'ext' / 'browser-captures' / 'gemini'))
    ap.add_argument('--out', default=str(REPO / 'lib' / 'markdown' / 'gemini' / 'conversations'))
    args = ap.parse_args()

    src = Path(args.browser_captures)
    if not src.is_dir():
        print(f'no gemini captures in {src} — nothing to copy')
        return
    out = Path(args.out)
    files = {}
    for d in sorted(p for p in src.iterdir() if p.is_dir()):
        for f in sorted(d.glob('*.md')):
            name = f.name if f.name not in files else f'{d.name}-{f.name}'
            files[name] = anchored(f.read_text())
    # reconcile, not wipe: unchanged scrapes keep their mtime (no needless iCloud
    # re-upload of the whole tree each run); departed ones are pruned as orphans
    w, u, r = reconcile_dir(out, files)
    print(f'gemini: {len(files)} scrape(s) to {out.relative_to(REPO)} (anchored) — '
          f'{w} written, {u} unchanged, {r} pruned')


if __name__ == '__main__':
    main()
