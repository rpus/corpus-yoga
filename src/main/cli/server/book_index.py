"""
book_index.py - `corpus-yoga server build`: data/output/markdown/index.md, the book index the server
serves, written from the judged index, data/output/indexing/indexed-semantic-concepts.json -
one alphabetised entry per located headword, its locators grouped by conversation, each a link
to the turn's durable anchor. The site's concept table is built from the same judged index.
"""
import sys
from pathlib import Path
import facts
import tier
import indexing

SELF = 'src/main/cli/server/book_index.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

INDEX_MD = tier.DATA / 'output' / 'markdown' / 'index.md'

# Show this many turn links per (headword, conversation) before folding the rest
# into a "+N more" note - book indexes cite, they do not enumerate.
LOCATORS_SHOWN = 4


def index_markdown(index: dict) -> str:
    """The judged index as the book index. No tier path in it: the index is a corpus
    artifact, and a machinery path in it would couple corpus bytes to the repo's layout."""
    lines = [
        '# Index',
        '',
        'Headwords are curated with `corpus-yoga indexing` (accept/reject; `build` '
        'judges the index) and this page is written by `corpus-yoga server build`. Locators link to durable turn anchors; '
        'labels are H*n*/A*n* (claude) and H*n*/G*n* (gemini).',
        '',
    ]
    letter = None
    for head, _aliases, locators in index['rows']:
        if not locators:
            continue
        first = head[0].upper() if head[0].isalpha() else '·'
        if first != letter:
            letter = first
            lines += [f'## {letter}', '']
        lines.append(f'### {head}')
        by_conversation: dict[str, list] = {}
        for rel, role, n, anchor in locators:
            by_conversation.setdefault(rel, []).append((role, n, anchor))
        for rel, hits in by_conversation.items():
            shown = [f'[{role}{n}]({rel}#{anchor})' for role, n, anchor in hits[:LOCATORS_SHOWN]]
            more = f' +{len(hits) - LOCATORS_SHOWN} more' if len(hits) > LOCATORS_SHOWN else ''
            lines.append(f'- [{Path(rel).stem}]({rel}#{hits[0][2]}) — {", ".join(shown)}{more}')
        lines.append('')
    lines += ['---', '', indexing.summary_of(index)]
    return '\n'.join(lines) + '\n'


def main() -> int:
    index = indexing.held_index()
    rel = INDEX_MD.relative_to(REPO) if INDEX_MD.is_relative_to(REPO) else INDEX_MD
    if index is None:
        facts.report(None, facts.act('server', 'build') + ': NOT DONE - ' + facts.phrase('no judged index - corpus-yoga indexing build writes it'))
        return 1
    text = index_markdown(index)
    if INDEX_MD.is_file() and INDEX_MD.read_text() == text:
        facts.report(None, facts.act('server', 'build') + ': DONE - ' + facts.phrase('no effect; {path} already holds the judged index', path=rel))
        return 0
    INDEX_MD.parent.mkdir(parents=True, exist_ok=True)
    INDEX_MD.write_text(text)
    facts.report(None, facts.act('server', 'build') + ': DONE - ' + facts.phrase('{path} written; {summary}', path=rel, summary=indexing.summary_of(index)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
