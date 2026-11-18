"""
status.py - bare `corpus-yoga server`: whether the markdown daemon runs, the render assets
present against their manifest (issues/759), the book index against the judged index it is
written from, and under now: the build once the judged index stands and index.md differs from
it, the stop while the daemon runs, the start where the corpus is rendered and the daemon is
down (issues/947, issues/960). Reads; writes nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import facts
import spell
import tier
import indexing
from book_index import INDEX_MD, index_markdown

SELF = 'src/main/cli/server/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]


@dataclass
class Assets:
    """The markdown viewer's render assets against their manifest, src/main/cli/server/serve_assets.txt."""
    present: str
    versions: list[str] | None = None
    absent: list[str] | str | None = None
    act: facts.Would | None = None


@dataclass
class BookIndex:
    """data/output/markdown/index.md against the judged index it is written from."""
    standing: str
    act: facts.Would | None = None


@dataclass
class Server:
    daemon: str = facts.named('serve_markdown daemon')
    act: facts.Would | None = None     # the stop or the start the daemon's state allows (issues/960)
    render_assets: Assets | None = None
    index: BookIndex | None = facts.named('index.md', default=None)


def book_index() -> BookIndex | None:
    """index.md's standing: what the judged index waits on, where it does not stand; current,
    where index.md holds what the judged index would write; the build otherwise. None where
    no corpus is projected."""
    if not (tier.DATA / 'output' / 'markdown').is_dir():
        return None
    waits = indexing.waits_on(indexing.ACCEPTED_FILE, indexing.REJECTED_FILE, indexing.MARKDOWN_DIR)
    if waits is not None:
        return BookIndex(waits)
    held = indexing.held_index()
    if held is not None and INDEX_MD.is_file() and INDEX_MD.read_text() == index_markdown(held):
        return BookIndex(facts.phrase('current - written from the judged index'))
    return BookIndex(facts.phrase('stale - the judged index moved since it was written'),
                     facts.Would(spell.line('server', 'build'), {'data/output/markdown/index.md': 1}))


@dataclass
class Status:
    server: Server
    now: dict | str = facts.phrase('none - nothing to do')   # every act the body names, gathered (issues/1028)


def daemon_act(running: bool, rendered: bool) -> facts.Would | None:
    """The act the daemon's state allows (issues/960): the stop while it runs; the start while
    the corpus page is rendered and it is down; none otherwise."""
    if running:
        return facts.Would(spell.line('server', 'stop'), {'serve_markdown daemon': 1})
    if rendered:
        return facts.Would(spell.line('server', 'start', daemon=True), {'data/output/markdown': 1})
    return None


def main() -> int:
    found = subprocess.run(['pgrep', '-f', 'serve_markdown.py'], capture_output=True, text=True).stdout.split()
    manifest = REPO / 'src' / 'main' / 'cli' / 'server' / 'serve_assets.txt'
    assets = REPO / 'ext' / 'lib' / 'serve_markdown'
    lines = [line.split('#', 1)[0].strip() for line in manifest.read_text().splitlines()]
    wanted = [(line.split()[0], line) for line in lines if line]
    missing = [name for name, _line in wanted if not (assets / name).is_file()]
    versions: list[str] = []
    for name, line in wanted:               # a version is the package and its pin in the asset's address
        for version in re.findall(r'/npm/([^/@]+@[^/]+)', line) if name not in missing else []:
            if version not in versions:
                versions.append(version)
    rendered = (tier.DATA / 'output' / 'markdown' / 'index.md').is_file()
    out = Status(Server(facts.phrase('running (pid {pid})', pid=found[0]) if found else facts.phrase('not running'), render_assets=Assets(
        facts.phrase('{got}/{total} in ext/lib/serve_markdown', got=len(wanted) - len(missing), total=len(wanted)), versions or None,
        (facts.phrase('all of them') if len(missing) == len(wanted) else missing) or None,
        facts.would(spell.line('server', 'ensure-assets'), {'ext/lib/serve_markdown': len(missing)}))))
    out.server.act = daemon_act(bool(found), rendered)
    out.server.index = book_index()
    out.now = facts.now_of(out) or facts.phrase('none - nothing to do')
    facts.say(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
