#!/usr/bin/env python
"""
status.py - bare `corpus-yoga site`: the publish tree against its sources, the corpus page and
the deploy mount, read as rows on stdin from site.sh, which holds what a page is (#759):
`pages <standing>`, `page <file> <standing>`, `index <title>` or `index ABSENT`,
`deploy <words>`, `land <file> <what changes>` for each file corpus-yoga site publish would
land on rpus.co (#881) - the corpus page one row per line of its comparison, `<part>: <words>`,
said as facts beneath the file - tab-separated. Reads; writes nothing.
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
    producer: facts.Command = facts.Command('corpus-yoga site render', facts.sentence('renders it'))


@dataclass
class Publish:
    """What corpus-yoga site publish would land on rpus.co: each file with what changes in it, and the act (#881)."""
    would_land: dict[str, str | dict[str, str]]
    remedy: facts.Command = facts.Command('corpus-yoga site publish', facts.sentence('would copy, commit and push them'))


@dataclass
class Site:
    publish_tree: str
    sources: str
    pages: dict[str, str] | str   # each stale page by its file, or that all are current
    index: CorpusPage | facts.Finding = facts.named('index.html')
    deploy: str = ''
    publish: Publish | str = facts.sentence('nothing to land - rpus.co holds the tree as assembled')


@dataclass
class Status:
    site: Site


def main() -> int:
    rows = [row.split('\t') for row in sys.stdin.read().splitlines() if row.strip()]
    stale = {row[1]: row[2] for row in rows if row[0] == 'page'}
    standing = next((row[1] for row in rows if row[0] == 'pages'), facts.sentence('current with rsc/site/'))
    title = next((row[1] for row in rows if row[0] == 'index'), 'ABSENT')
    index: CorpusPage | facts.Finding = CorpusPage(title)
    if title == 'ABSENT':
        index = facts.Finding(facts.sentence('absent - the corpus page is unbuilt'),
                              facts.Command('corpus-yoga pipeline run', facts.sentence('renders it, or corpus-yoga site render')))
    land: dict[str, str | dict[str, str]] = {}
    for row in rows:
        if row[0] != 'land' or len(row) < 3:
            continue
        said = {} if ': ' in row[2] or row[1] in land else None
        if said is None and row[1] not in land:
            land[row[1]] = row[2]
            continue
        parts = land.setdefault(row[1], {})
        if isinstance(parts, str):
            parts = land[row[1]] = {}
        key, _, words = row[2].partition(': ')
        parts[key] = words.replace(': ', ' - ') if words else key
    site = Site('data/output/site/ (rpus.co)', 'rsc/site/', stale or standing, index,
                next((row[1] for row in rows if row[0] == 'deploy'), ''))
    if land:
        site.publish = Publish(land)
    elif site.deploy != facts.sentence("the mount ext/mnt/site is present, rpus.co's clone"):
        site.publish = facts.sentence('nothing can land - no clone of rpus.co is mounted')
    facts.say(Status(site))
    return 0


if __name__ == '__main__':
    sys.exit(main())
