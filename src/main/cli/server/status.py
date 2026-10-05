#!/usr/bin/env python
"""
status.py - bare `corpus-yoga server`: whether the markdown daemon runs, and the render assets
present against their manifest (#759). Reads; writes nothing.
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
    facts.say(Status(Server(f'running (pid {found[0]})' if found else 'not running', Assets(
        f'{len(wanted) - len(missing)}/{len(wanted)} in ext/lib/serve_markdown', versions or None, ('all of them' if len(missing) == len(wanted) else missing) or None,
        facts.Command('corpus-yoga server ensure-assets', 'fetches them; the next corpus-yoga server start does too') if missing else None))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
