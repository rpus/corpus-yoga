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
import subprocess  # noqa: E402
import facts  # noqa: E402


@dataclass
class Server:
    daemon: str = facts.named('serve_markdown daemon')
    render_assets: str = ''       # a file tally against the manifest; corpus-yoga prerequisites reports the versions


@dataclass
class Status:
    server: Server


def main() -> int:
    found = subprocess.run(['pgrep', '-f', 'serve_markdown.py'], capture_output=True, text=True).stdout.split()
    manifest = REPO / 'src' / 'main' / 'model' / 'serve_assets.txt'
    assets = REPO / 'ext' / 'lib' / 'serve_markdown'
    names = [line.split('#', 1)[0].split()[0] for line in manifest.read_text().splitlines() if line.split('#', 1)[0].split()]
    present = sum(1 for name in names if (assets / name).is_file())
    facts.say(Status(Server(f'running (pid {found[0]})' if found else 'not running',
                            f'{present}/{len(names)} present in ext/lib/serve_markdown')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
