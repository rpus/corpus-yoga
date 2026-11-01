#!/usr/bin/env python
"""
status.py - bare `corpus-yoga site`: the publish tree against its sources, the corpus page and
the deploy mount, read as rows on stdin from site.sh, which holds what a page is (issues/759):
`pages absent <standing>` where the publish tree is absent, `page <file> <standing>`, `index <title>` or `index ABSENT`,
`deploy <words>`, `land <file> <what changes>` for each file corpus-yoga site publish would
land on rpus.co (issues/881) - the corpus page one row per line of its comparison, `<part>: <words>`,
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
import spell  # noqa: E402
import tier  # noqa: E402
import page_declaration as declared  # noqa: E402 - what the page declares, read back against the corpus (issues/1000)


@dataclass
class CorpusPage:
    title: str = facts.named('the corpus page')
    producer: facts.Command = facts.Command(spell.line('site', 'render'), facts.phrase('renders it'))


@dataclass
class Publish:
    """What corpus-yoga site publish would land on rpus.co: each file with what changes in it, and the act (issues/881)."""
    would_land: dict[str, str | dict[str, str]]
    remedy: facts.Command = facts.Command(spell.line('site', 'publish'), facts.phrase('would copy, commit and push them'))


@dataclass
class Site:
    publish_tree: str
    sources: str
    pages: dict[str, str] | str   # each stale page by its file, or that all are current
    index: CorpusPage | facts.Finding = facts.named('index.html')
    lags: dict[str, dict[str, str] | str] | str = facts.phrase('unread - no page and no corpus to compare')   # the page's declarations against the corpus (issues/1000)
    deploy: str = ''
    publish: Publish | str = facts.phrase('nothing to land - rpus.co holds the tree as assembled')


@dataclass
class Status:
    site: Site
    now: dict[str, dict[str, dict[str, int]]] | str = facts.phrase('none - nothing to do')   # the standing (issues/947): the sync where the publish tree is absent, the publish while one would land (issues/998)


def read_lag(site: Site) -> bool:
    """The page's declarations against the corpus now (issues/1000), said under lags: - each
    conversation whose metrics moved, a regression as a warning, the absent and the gone -
    and whether any lag stands. The page and the corpus are read from the tiers in force."""
    page_file = tier.DATA / 'output' / 'site' / 'index.html'
    md_root = tier.DATA / 'output' / 'markdown'
    if not page_file.is_file() or not md_root.is_dir():
        return False
    page = declared.page_declarations(page_file.read_text())
    if page is None:
        site.lags = facts.phrase('unread - the page declares no counts; corpus-yoga site render declares them')
        return True
    corpus = declared.corpus_declarations(md_root)
    found = declared.lag(page, corpus)
    if not found:
        site.lags = facts.phrase('none - current with the corpus ({n} conversation(s))', n=len(corpus))
        return False
    said: dict[str, dict[str, str] | str] = {}
    for cid, moved in found.regressed.items():
        said[cid] = {metric: facts.phrase('WARN - regressed from {old} to {new}', old=old, new=new) for metric, (old, new) in moved.items()}
    for cid, moved in found.lagging.items():
        said[cid] = {metric: facts.phrase('{old} to {new}', old=old, new=new) for metric, (old, new) in moved.items()}
    for cid in found.absent_from_page:
        said[cid] = facts.phrase('absent from the page')
    for cid in found.gone_from_corpus:
        said[cid] = facts.phrase('gone from the corpus')
    site.lags = said
    return True


def main() -> int:
    rows = [row.split('\t') for row in sys.stdin.read().splitlines() if row.strip()]
    stale = {row[1]: row[2] for row in rows if row[0] == 'page'}
    absent = any(row[0] == 'pages' and row[1] == 'absent' for row in rows)
    standing = next((row[2] for row in rows if row[0] == 'pages'), facts.phrase('current with rsc/site/'))
    title = next((row[1] for row in rows if row[0] == 'index'), 'ABSENT')
    index: CorpusPage | facts.Finding = CorpusPage(title)
    if title == 'ABSENT':
        index = facts.Finding(facts.phrase('absent - the corpus page is unbuilt'),
                              facts.Command(spell.line('pipeline', 'run'), facts.phrase('renders it, or corpus-yoga site render')))
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
                deploy=next((row[1] for row in rows if row[0] == 'deploy'), ''))
    lagging = read_lag(site)
    if land:
        site.publish = Publish(land)
    elif site.deploy != facts.phrase("the mount ext/mnt/site is present, rpus.co's clone"):
        site.publish = facts.phrase('nothing can land - no clone of rpus.co is mounted')
    out = Status(site)
    now: dict[str, dict[str, dict[str, int]]] = {}
    if absent:
        now[spell.line('site', 'sync')] = {'would assemble': {'data/output/site/': 1}}
    if lagging:
        # the render is the room's standing while the page lags the corpus (issues/1000), before
        # the publish: what would be published is the lag otherwise
        now[spell.line('site', 'render')] = {'would render': {'index.html': 1}}
    if land and not absent:
        # the publish is the room's standing while one would land (issues/998): by page, so that
        # the bare status names it beside the room's other acts
        now[spell.line('site', 'publish')] = {'would publish': {page: 1 for page in land}}
    if now:
        out.now = now
    facts.say(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
