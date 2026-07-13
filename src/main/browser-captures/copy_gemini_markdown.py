#!/usr/bin/env python
"""
copy_gemini_markdown.py — copy gemini scrape markdown into the presentation tree
(output/markdown/gemini/chat/conversations, beside claude's projections), anchoring each turn heading:

    ## Human (3)   ->   ## Human (3) <a id="human-3"></a>

Gemini has no API and so no message uuids; the role-count anchor is the best turn
identity available, and gemini conversations are append-only (the audit tail-probe
already relies on this), so an anchor never moves — later captures only add turns.
Anchors ride the heading line, where compare_markdown.turn_seq's `## <Role> [^\\n]*`
split ignores them. The input/ scrapes themselves are data and are left untouched;
this derived copy is the navigable/indexable surface.

Files are named '<NN>-<slug>.md', paralleling claude's ordinals: the numbering comes
from the ordering CAPTURE (input/gemini/chat/browser-DOM/ordering.txt — the web-UI
listing, reversed to ascending; refresh via the listing sweep), zero-padded to the
corpus width so lexicographic order == conversation order. Ordinals are presentation
and renumber as the corpus changes; the gemini app id (the <url> line) is the
identity. Captured conversations absent from the ordering append after it,
id-sorted; a residual filename collision gets the id prefixed (the old rule).

Usage:
  src/run_python_script.sh src/main/browser-captures/copy_gemini_markdown.py \
    [--browser-dom input/gemini/chat/browser-DOM] [--out cache/markdown/gemini]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import REPO, MD033_PRAGMA, reconcile_dir

HEADING = re.compile(r'^## (Human|Gemini) \((\d+)\)$', flags=re.M)


def ordering(captures_dir: Path) -> dict:
    """{conversation id: ordinal} from the ordering capture; {} where none exists
    (files then get no numeric prefix — the pre-ordering behaviour)."""
    f = captures_dir / 'ordering.txt'
    if not f.exists():
        return {}
    ids = [l.strip() for l in f.read_text().splitlines()
           if l.strip() and not l.startswith('#')]
    return {cid: n for n, cid in enumerate(ids, 1)}


def anchored(md):
    md = HEADING.sub(lambda m: f'## {m[1]} ({m[2]}) <a id="{m[1].lower()}-{m[2]}"></a>', md)
    # same lint pragma as render() emits, inserted after the title line (the scrapes in
    # input/ stay pristine; only this derived copy carries presentation dressing)
    first, _, rest = md.partition('\n')
    return f'{first}\n\n{MD033_PRAGMA}\n\n{rest.lstrip()}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--browser-dom', default=str(REPO / 'input' / 'gemini' / 'chat' / 'browser-DOM'))
    ap.add_argument('--out', default=str(REPO / 'output' / 'markdown' / 'gemini' / 'chat' / 'conversations'))
    args = ap.parse_args()

    src = Path(args.browser_dom)
    if not src.is_dir():
        print(f'no gemini captures in {src} — nothing to copy')
        return
    out = Path(args.out)
    order = ordering(src)
    dirs = sorted((p for p in src.iterdir() if p.is_dir()),
                  key=lambda d: (order.get(d.name, len(order) + 1), d.name))
    # captured-but-unlisted conversations continue the numbering after the ordering,
    # id-sorted, so every file gets a stable-within-this-corpus ordinal
    tail = (n for n in range(len(order) + 1, len(order) + 1 + len(dirs)))
    ordinals = {d.name: order.get(d.name) or next(tail) for d in dirs}
    width = len(str(max(len(order), len(dirs)))) if (order or dirs) else 1
    files = {}
    for d in dirs:
        for f in sorted(d.glob('*.md')):
            prefix = f'{ordinals[d.name]:0{width}d}-' if order else ''
            name = f'{prefix}{f.name}'
            if name in files:
                name = f'{prefix}{d.name}-{f.name}'
            files[name] = anchored(f.read_text())
    # reconcile, not wipe: unchanged scrapes keep their mtime (no needless iCloud
    # re-upload of the whole tree each run); departed ones are pruned as orphans
    w, u, r = reconcile_dir(out, files)
    print(f'gemini: {len(files)} scrape(s) to {out.relative_to(REPO)} (anchored) — '
          f'{w} written, {u} unchanged, {r} pruned')


if __name__ == '__main__':
    main()
