"""
project_markdown.py - place gemini's rendered scrapes in the presentation tree (the gemini counterpart of src/main/project_markdown.py)
(data/output/markdown/gemini/chat/conversations, beside claude's projections). Each scrape
is rendered by the run, its turn headings anchored, at its cache address
(src/main/browser/gemini/render.py); this names and places the renderings. Anchors ride
the heading line, where markdown_projection.turn_seq's `## <Role> [^\\n]*` split ignores
them. The data/input/ scrapes themselves are data and are left untouched; this derived
copy is the navigable/indexable surface.

Files are named '<NN>-<slug>.md', paralleling claude's ordinals: the numbering comes
from the ordering CAPTURE (data/input/gemini/chat/DOM-capture/ordering.txt — the web-UI
listing, reversed to ascending; refresh via the listing sweep), zero-padded to the
corpus width so lexicographic order == conversation order. Ordinals are presentation
and renumber as the corpus changes; the gemini app id (the <url> line) is the
identity. Captured conversations absent from the ordering append after it,
id-sorted; a residual filename collision gets the id prefixed (the old rule).

Usage:
  src/run_python_script.sh src/main/browser/gemini/project_markdown.py \
    [--dom-capture data/input/gemini/chat/DOM-capture] [--out cache/markdown/gemini]
"""
import argparse
import json
import sys
from pathlib import Path
import tier  # the tiers, one home (issues/702)
from markdown_projection import FACTS, RENDERINGS, deposit, turn_extent, conv_id

REPO_ROOT = tier.REPO

def ordering(captures_dir: Path) -> dict:
    """{conversation id: ordinal} from the ordering capture; {} where none exists
    (files then get no numeric prefix — the pre-ordering behaviour)."""
    f = captures_dir / 'ordering.txt'
    if not f.exists():
        return {}
    ids = [l.strip() for l in f.read_text().splitlines()
           if l.strip() and not l.startswith('#')]
    return {cid: n for n, cid in enumerate(ids, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dom-capture', default=str(tier.DATA / 'input' / 'gemini' / 'chat' / 'DOM-capture'))
    ap.add_argument('--out', default=str(tier.DATA / 'output' / 'markdown' / 'gemini' / 'chat' / 'conversations'))
    args = ap.parse_args()

    src = Path(args.dom_capture)
    if not src.is_dir():
        print(f'no gemini captures in {src} — nothing to copy')
        return 0
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
    n_bad = 0
    unrendered = [d.name for d in dirs if any(d.glob('*.md')) and not (tier.cache_of(d) / FACTS).is_file()]
    if unrendered:
        # depositing without a scrape's rendering would prune its conversation's file
        sys.exit(f"no rendering at the cache address of {len(unrendered)} scrape(s) - {', '.join(unrendered)}; "
                 f"corpus-yoga pipeline run renders each")
    for d in dirs:
        cache = tier.cache_of(d)
        record = json.loads((cache / FACTS).read_text()) if (cache / FACTS).is_file() else {}
        for scrape, held in sorted(record.items()):
            prefix = f'{ordinals[d.name]:0{width}d}-' if order else ''
            name = f'{prefix}{scrape}'
            if name in files:
                name = f'{prefix}{d.name}-{scrape}'
            if held['problems']:     # held to the family as claude's projections are (issues/965)
                n_bad += 1
                print(f"  INVALID {name}: {'; '.join(held['problems'])}", file=sys.stderr)
            files[name] = (cache / RENDERINGS / scrape).read_text()
    # L4, one step down from the capture guard: the projection never shrinks either.
    # Matched by conversation id and not by filename, because the ordinal prefix
    # renumbers as the corpus grows -- a shorter rendering would otherwise arrive under
    # a new name and the longer one be pruned as an orphan, which is the same loss with
    # an extra step. Keeping the longer text under the NEW name preserves the
    # renumbering while refusing the shrink.
    standing = {}
    for f in (out.glob('*.md') if out.is_dir() else []):
        text = f.read_text()
        cid = conv_id(text)
        if cid:
            standing[cid] = text
    for name, text in list(files.items()):
        was = standing.get(conv_id(text) or '')
        if was is None:
            continue
        old_extent, new_extent = turn_extent(was), turn_extent(text)
        if new_extent[0] < old_extent[0] or new_extent[1] < old_extent[1]:
            files[name] = was
            print(f'REFUSED: {name}: the capture renders {new_extent[0]} human turns of '
                  f'{new_extent[1]}, against {old_extent[0]} of {old_extent[1]} already '
                  f'projected — an append-only conversation cannot shrink, so the capture '
                  f'under data/input/ is short. The projection is left as it stands; '
                  f'recapture before trusting either.')

    # deposit, not wipe: unchanged scrapes keep their mtime (no needless iCloud
    # re-upload of the whole tree each run). Identity is conv_id (issues/419): a
    # renumbered ordering renames every output, and 27 renames once printed as
    # '27 pruned' — indistinguishable from a purge in the one line that mattered.
    deposit(out, files, f'gemini: {len(files)} scrape(s)', identity=conv_id, note=' (anchored)',
            because='its capture departed from data/input/gemini/chat/DOM-capture/')
    print(f'rendered {len(files)} scrapes to {out} ({n_bad} invalid)')
    return 1 if n_bad else 0


if __name__ == '__main__':
    sys.exit(main())
