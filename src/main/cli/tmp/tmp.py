"""
tmp.py (corpus-yoga tmp) - the room's tmp/, what lasts one run, as the cache, the logs and the
stage have their nouns (issues/1170).

    corpus-yoga tmp                     # status: the tier, each working file a run that died left, and what to run next
    corpus-yoga tmp clean               # remove the files the status names

A script keeps a working file only while it runs, through the tier's scratch_file and
scratch_dir (src/main/tier.sh, issues/906): under tmp/<command>/<verb>/, the act the launcher
dispatched, or tmp/<script>/ where it dispatched none, named <name>.<pid>.<random> with the
pid of the run that keeps it. A run that dies before removing its file leaves it there, and
a file so named whose pid no process holds is an orphan the status names and the cleaner,
which takes no flag, removes through the one loop every clean verb runs (src/main/cleaner.py).
An entry not so named is its command's own - the forge's worktrees under tmp/forge - and never
this noun's.
"""
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from declared_parser import command_parser
import cleaner  # the one loop every clean verb runs (issues/837)
import facts
import spell
import tier

SELF = 'src/main/cli/tmp/tmp.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

KINDS = {'orphan': 'orphans'}
RUN_FILE = re.compile(r'.+\.(\d+)\.[A-Za-z0-9]{6,}')   # <name>.<pid>.<random>, as mktemp makes it


def size_of(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        return path.lstat().st_size
    return sum(f.lstat().st_size for f in path.rglob('*') if f.is_file() or f.is_symlink())


def human(n: float) -> str:
    for unit in ('B', 'K', 'M'):
        if n < 1024:
            return f'{n:.0f}{unit}' if unit == 'B' else f'{n:.1f}{unit}'
        n /= 1024
    return f'{n:.1f}G'


def lives(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def orphans(root: Path) -> list[Path]:
    """Each working file under root/<command>/ or root/<command>/<verb>/ whose run is gone: named
    <name>.<pid>.<random>, its pid held by no process."""
    if not root.is_dir():
        return []
    found = []
    for command in sorted(d for d in root.iterdir() if d.is_dir() and not d.is_symlink()):
        for entry in sorted(command.iterdir()):
            beneath = sorted(entry.iterdir()) if entry.is_dir() and not entry.is_symlink() and not RUN_FILE.fullmatch(entry.name) else [entry]
            for candidate in beneath:
                named = RUN_FILE.fullmatch(candidate.name)
                if named and not lives(int(named.group(1))):
                    found.append(candidate)
    return found


@dataclass
class Orphan:
    size: str
    why: str = facts.phrase('a working file whose run is gone')
    act: facts.Would | None = None


@dataclass
class Status:
    """Bare corpus-yoga tmp: the tier, each orphan by its path, and under now: the cleaner over
    what it would remove, by path - the shape the cache's and the logs' statuses have, so that
    the room's one reading, which folds this block, names a file a dead run left."""
    tmp: str = facts.named('tmp')
    orphans: dict[str, Orphan] | None = None
    now: dict | str | None = None


def status_facts() -> Status:
    root = tier.TMP
    if not root.is_dir():
        return Status(facts.phrase('absent - no run has kept a working file'), {}, facts.phrase('none - nothing to do'))
    found = {rel: Orphan(human(size_of(p)), act=facts.Would(spell.line('tmp', 'clean'), {rel: 1}))
             for p in orphans(root) for rel in (p.relative_to(REPO).as_posix() if p.is_relative_to(REPO) else str(p),)}
    directories = sum(1 for d in root.iterdir() if d.is_dir())
    said = (facts.phrase('{n} directory(ies), {size}, {orphans} orphan(s)', n=directories, size=human(size_of(root)), orphans=len(found)) if found
            else facts.phrase('{n} directory(ies), {size}', n=directories, size=human(size_of(root))))
    out = Status(said, found)
    out.now = facts.now_of(out) or facts.phrase('none - nothing to do')
    return out


def _dispose(path: Path) -> str | None:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
    except OSError as e:
        return (e.strerror or str(e)).lower()
    return None if not (path.exists() or path.is_symlink()) else 'still present'


def entries() -> list[cleaner.Entry]:
    """Everything the janitor acts on: each orphan by its path, with its size."""
    return [cleaner.Entry('orphan', rel, {'orphan': facts.phrase('a working file whose run is gone'), 'size': human(size_of(p))},
                          lambda p=p: _dispose(p), rel)
            for p in orphans(tier.TMP) for rel in (p.relative_to(REPO).as_posix() if p.is_relative_to(REPO) else str(p),)]


def main() -> int:
    args = command_parser('tmp').parse_args()
    if args.verb == 'clean':
        return cleaner.clean('tmp', entries(), KINDS)
    facts.say(status_facts())
    return 0


if __name__ == '__main__':
    sys.exit(main())
