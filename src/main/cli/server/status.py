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

SELF = 'src/main/cli/server/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import re  # noqa: E402
import subprocess  # noqa: E402
import facts  # noqa: E402
import tier  # noqa: E402


@dataclass
class Assets:
    """The markdown viewer's render assets against their manifest, src/main/model/serve_assets.txt."""
    present: str
    versions: list[str] | None = None
    absent: list[str] | str | None = None
    remedy: facts.Command | None = None


@dataclass
class Server:
    daemon: str = facts.named('serve_markdown daemon')
    render_assets: Assets | None = None


@dataclass
class Status:
    server: Server
    now: dict[str, dict[str, dict[str, int]]] | str = facts.phrase('none - nothing to do')   # the standing (issues/947)


def now_of(running: bool, rendered: bool) -> dict[str, dict[str, dict[str, int]]] | str:
    """The server's standing (issues/960): the stop while the daemon runs; the start while the
    corpus page is rendered and the daemon is down; none otherwise."""
    if running:
        return {'corpus-yoga server stop': {'would stop': {'serve_markdown daemon': 1}}}
    if rendered:
        return {'corpus-yoga server start --daemon': {'would serve': {'data/output/markdown': 1}}}
    return facts.phrase('none - nothing to do')


def main() -> int:
    found = subprocess.run(['pgrep', '-f', 'serve_markdown.py'], capture_output=True, text=True).stdout.split()
    manifest = REPO / 'src' / 'main' / 'model' / 'serve_assets.txt'
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
    out = Status(Server(facts.phrase('running (pid {pid})', pid=found[0]) if found else facts.phrase('not running'), Assets(
        facts.phrase('{got}/{total} in ext/lib/serve_markdown', got=len(wanted) - len(missing), total=len(wanted)), versions or None,
        (facts.phrase('all of them') if len(missing) == len(wanted) else missing) or None,
        facts.Command('corpus-yoga server ensure-assets', facts.phrase('fetches them; the next corpus-yoga server start does too')) if missing else None)),
                 now_of(bool(found), rendered))
    facts.say(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
