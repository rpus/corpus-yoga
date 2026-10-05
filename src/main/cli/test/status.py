#!/usr/bin/env python
"""
status.py - bare `corpus-yoga test`: the checks and their committed expectation, and the two
hooks `corpus-yoga test install-hook` installs, each as it stands (#759, #778). Reads; writes
nothing.
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
class Hook:
    """One of the two hooks `corpus-yoga test install-hook` installs: whether it stands as
    installed, and the remedy where it does not. The home of the hooks' state (#778): the
    machine report and the forge say what this says."""
    installed: str
    remedy: facts.Command | None = None

    @property
    def sound(self) -> bool:
        return self.installed.startswith('yes')


@dataclass
class Test:
    checks: Checks
    commit: Hook = facts.named('pre-commit hook')       # the commit gate: a copy of rsc/test/pre-commit-hook.sh
    signature: Hook = facts.named('signature hook')     # the Signature's stamp: a symlink to rsc/test/prepare-commit-msg-hook.sh


@dataclass
class Status:
    test: Test


INSTALL = 'corpus-yoga test install-hook'


def _hook_path(name: str) -> Path | None:
    """Where git reads the named hook for this checkout; None where this is no git clone."""
    asked = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--git-path', f'hooks/{name}'], capture_output=True, text=True)
    if asked.returncode != 0 or not asked.stdout.strip():
        return None
    hook = Path(asked.stdout.strip())
    return hook if hook.is_absolute() else REPO / hook


def commit_hook() -> Hook:
    """The pre-commit hook, installed as a copy: a symlink is not it - a rename dangles one
    and git then skips it in silence."""
    hook = _hook_path('pre-commit')
    if hook is None:
        return Hook('no - not a git clone, so no hook to install')
    if hook.is_symlink():
        return Hook(f'as a symlink to {os.readlink(hook)} - a rename dangles it and git then skips it in silence',
                    facts.Command(INSTALL, 'reinstalls it'))
    if hook.is_file() and hook.read_bytes() == (REPO / 'rsc' / 'test' / 'pre-commit-hook.sh').read_bytes():
        return Hook('yes - a copy of rsc/test/pre-commit-hook.sh, which runs corpus-yoga test run')
    if hook.exists():
        return Hook('no - another pre-commit hook stands in its place', facts.Command(INSTALL, 'replaces it'))
    return Hook('no - nothing vets a commit', facts.Command(INSTALL, 'installs it'))


def signature_hook() -> Hook:
    """The prepare-commit-msg hook, installed as a symlink to the script of the checkout
    that holds the hooks."""
    hook = _hook_path('prepare-commit-msg')
    if hook is None:
        return Hook('no - not a git clone, so no hook to install')
    script = hook.parent.parent.parent / 'rsc' / 'test' / 'prepare-commit-msg-hook.sh'
    if hook.is_symlink():
        link = Path(os.readlink(hook))
        target = link if link.is_absolute() else hook.parent / link
        if target.parent.resolve() / target.name == script.parent.resolve() / script.name:
            return Hook('yes - the symlink to rsc/test/prepare-commit-msg-hook.sh')
        return Hook(f'no - its symlink points elsewhere ({link})', facts.Command(INSTALL, 'reinstalls it'))
    if hook.exists():
        return Hook('no - another prepare-commit-msg hook stands in its place', facts.Command(INSTALL, 'replaces it'))
    return Hook('no - a commit goes unstamped by its Signature', facts.Command(INSTALL, 'installs it'))


def main() -> int:
    run = (REPO / 'src' / 'test' / 'dev' / 'run.py').read_text()
    facts.say(Status(Test(Checks(f"{len(re.findall(r'^def check_', run, re.M))} check sections"), commit_hook(), signature_hook())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
