#!/usr/bin/env python
"""
status.py - bare `corpus-yoga site`: the publish tree against its sources, the corpus page and
the deploy mount, read as rows on stdin from site.sh, which holds what a page is (issues/759):
`pages absent <standing>` where the publish tree is absent, `page <file> <standing>`, `index <title>` or `index ABSENT`,
`deploy <words>`, `fetch <words>` where rpus.co could not be read as it stands, `clone <words>
[<command> <what it does>]` where the clone stands to its origin (issues/1020), `land <file> <what
changes>` for each file corpus-yoga site publish would land on rpus.co (issues/881) - the corpus
page one row per line of its comparison, `<part>: <words>`, said as facts beneath the file -
tab-separated. Reads; writes nothing but the clone's record of rpus.co, which site.sh fetches.
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
    remedy: facts.Would | None = None     # the render, while the page lags the corpus (issues/1000)


@dataclass
class Site:
    publish_tree: str
    sources: str
    pages: dict | str   # each stale page by its file, that all are current, or absent with the act that assembles them
    index: CorpusPage | facts.Finding = facts.named('index.html')
    lags: dict[str, dict[str, str] | str] | dict[str, str | facts.Would] | str = facts.phrase('unread - no page and no corpus to compare')   # the page's declarations against the corpus (issues/1000)
    deploy: str = ''
    fetch: str | None = None      # where rpus.co could not be read as it stands, and so is read as last fetched (issues/1020)
    clone: str | facts.Finding | None = None   # where the clone stands to the branch rpus.co serves; a finding where publish refuses it
    publish: dict | str = facts.phrase('nothing to land - rpus.co holds the tree as assembled')   # what would land, under the act that lands it (issues/881, issues/1028)


@dataclass
class Status:
    site: Site
    now: dict | str = facts.phrase('none - nothing to do')   # every act the body names, gathered (issues/1028)


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
    try:
        corpus = declared.corpus_declarations(md_root)
    except KeyError:
        # a render before the turn counts' home (issues/1001): the run re-renders the corpus, the counts with it
        site.lags = {'unread': facts.phrase('the corpus predates its turn counts by role'),
                     'remedy': facts.Would(spell.line('pipeline', 'run'), {'data/output/markdown': 1})}
        return False
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
        index = facts.Finding(facts.phrase('absent - the corpus page is unbuilt'), facts.Would(spell.line('site', 'render'), {'index.html': 1}))
    land: dict = {}
    for row in rows:
        if row[0] != 'land' or len(row) < 3:
            continue
        at = land                 # the file, then the keys the comparison's fact stands under, then its value (issues/1028)
        for key in row[1:-2]:
            if not isinstance(at.get(key), dict):
                at[key] = {}
            at = at[key]
        at[row[-2]] = row[-1]
    site = Site('data/output/site/ (rpus.co)', 'rsc/site/', stale or standing, index,
                deploy=next((row[1] for row in rows if row[0] == 'deploy'), ''))
    site.fetch = next((row[1] for row in rows if row[0] == 'fetch'), None)
    position = next((row for row in rows if row[0] == 'clone'), None)
    refused = position is not None and len(position) >= 4      # a clone publish refuses: no served branch, another branch, diverged
    if position is not None:
        site.clone = facts.Finding(position[1], facts.Command(position[2], position[3])) if refused else position[1]
    if absent:
        site.pages = {'state': standing, 'remedy': facts.Would(spell.line('site', 'sync'), {'data/output/site/': 1})}
    if read_lag(site) and isinstance(site.index, CorpusPage):
        site.index.remedy = facts.Would(spell.line('site', 'render'), {'index.html': 1})   # before the publish: what would land is the lag otherwise
    if land and not absent and not refused:
        # what would land, each file with what changes in it, under the act that lands it (issues/881,
        # issues/998); a clone the publish refuses has its finding instead
        site.publish = {'remedy': facts.Would(spell.line('site', 'publish'), land)}
    elif land:
        site.publish = land
    elif site.deploy != facts.phrase("the mount ext/mnt/site is present, rpus.co's clone"):
        site.publish = facts.phrase('nothing can land - no clone of rpus.co is mounted')
    out = Status(site)
    out.now = facts.now_of(out) or facts.phrase('none - nothing to do')
    facts.say(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
