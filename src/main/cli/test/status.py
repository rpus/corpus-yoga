#!/usr/bin/env python
"""
status.py - bare `corpus-yoga test`: the checks and their committed expectation, and whether
the commit hook is installed (#759). Reads; writes nothing.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/test/status.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import os  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import facts  # noqa: E402


@dataclass
class Checks:
    sections: str = facts.named('src/test/dev/run.py')
    expectation: str = 'rsc/test/run_expected_checks'
    report: str = 'rsc/test/run.log'
    xrefs: str = 'rsc/test/xref.csv'


@dataclass
class Test:
    checks: Checks
    hook: str
    remedy: facts.Command | None = None


@dataclass
class Status:
    test: Test


def main() -> int:
    run = (REPO / 'src' / 'test' / 'dev' / 'run.py').read_text()
    asked = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--git-path', 'hooks/pre-commit'], capture_output=True, text=True)
    hook = Path(asked.stdout.strip()) if asked.returncode == 0 and asked.stdout.strip() else None
    if hook is not None and not hook.is_absolute():
        hook = REPO / hook
    installed = hook is not None and hook.is_symlink()
    facts.say(Status(Test(
        Checks(f"{len(re.findall(r'^def check_', run, re.M))} check sections"),
        f'installed, a link to {os.readlink(hook)}' if installed and hook is not None else 'not installed',
        None if installed else facts.Command('corpus-yoga test install-hook'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
