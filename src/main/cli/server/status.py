#!/usr/bin/env python
"""
status.py - bare `corpus-yoga server`: whether the markdown daemon runs, the render assets
present against their manifest (issues/759), and under now: the stop while the daemon runs,
the start where the corpus is rendered and the daemon is down (issues/947, issues/960).
Reads; writes nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import facts
import spell
import tier

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
class Server:
    daemon: str = facts.named('serve_markdown daemon')
    act: facts.Would | None = None     # the stop or the start the daemon's state allows (issues/960)
    render_assets: Assets | None = None


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
        facts.Would(spell.line('server', 'ensure-assets'), {'ext/lib/serve_markdown': len(missing)}) if missing else None)))
    out.server.act = daemon_act(bool(found), rendered)
    out.now = facts.now_of(out) or facts.phrase('none - nothing to do')
    facts.say(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
