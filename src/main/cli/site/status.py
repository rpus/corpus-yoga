#!/usr/bin/env python
"""
status.py - bare `corpus-yoga site`: the publish tree against its sources, the corpus page and
the deploy mount, read as rows on stdin from site.sh, which holds what a page is (#759):
`pages <standing>`, `page <file> <standing>`, `index <title>` or `index ABSENT`,
`deploy <words>`, tab-separated. Reads; writes nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/site/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import facts  # noqa: E402


@dataclass
class CorpusPage:
    title: str = facts.named('the corpus page')
    producer: facts.Command = facts.Command('corpus-yoga site render', 'renders it')


@dataclass
class Site:
    publish_tree: str
    sources: str
    pages: dict[str, str] | str   # each stale page by its file, or that all are current
    index: CorpusPage | facts.Finding = facts.named('index.html')
    deploy: str = ''


@dataclass
class Status:
    site: Site


def main() -> int:
    rows = [row.split('\t') for row in sys.stdin.read().splitlines() if row.strip()]
    stale = {row[1]: row[2] for row in rows if row[0] == 'page'}
    standing = next((row[1] for row in rows if row[0] == 'pages'), 'current with rsc/site/')
    title = next((row[1] for row in rows if row[0] == 'index'), 'ABSENT')
    index: CorpusPage | facts.Finding = CorpusPage(title)
    if title == 'ABSENT':
        index = facts.Finding('absent - the corpus page is unbuilt',
                              facts.Command('corpus-yoga pipeline run', 'renders it, or corpus-yoga site render'))
    facts.say(Status(Site('data/output/site/ (rpus.co)', 'rsc/site/', stale or standing, index,
                          next((row[1] for row in rows if row[0] == 'deploy'), ''))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
