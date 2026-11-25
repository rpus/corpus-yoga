"""
tmp.py (corpus-yoga tmp) - the room's tmp/, what lasts one run, as the cache, the logs and the
stage have their nouns (issues/1170).

    corpus-yoga tmp                     # status: each entry under tmp/ with its size, each orphan, and what to run next
    corpus-yoga tmp clean               # remove the orphans the status names

A script keeps a working file or directory only while it runs, through the tier's scratch_file
and scratch_dir (src/main/tier.sh, issues/906): directly under tmp/, named
<act>.<name>.<pid>.<random> - the act the launcher dispatched, <command>.<verb>, or the running
script where it dispatched none - with the pid of the run that keeps it, and no directory made for
it. One whose pid no process holds was left by a run that died, an orphan. A command that keeps a
directory under tmp/ declares it - the forge's worktrees under tmp/forge, as its merge and rebase
write - and any other entry directly under tmp/ is an orphan too: no command keeps it. The status
names each entry with its size and each orphan with why; the cleaner, which takes no flag, removes
the orphans through the one loop every clean verb runs (src/main/cleaner.py).
"""
import json
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


def keepers() -> set[str]:
    """The directories a command keeps directly under tmp/, as its declaration's r and w rows name
    them - tmp/<directory>/..."""
    kept = set()
    for declaration in (REPO / 'src' / 'main' / 'cli').glob('*/*.json'):
        rows = json.loads(declaration.read_text())
        for row in [*rows.get('r', []), *rows.get('w', [])]:
            parts = row.split('/')
            if parts[0] == 'tmp' and len(parts) > 1:
                kept.add(parts[1])
    return kept


def orphans(root: Path, kept: set[str]) -> list[tuple[Path, str]]:
    """Each orphan directly under root, with why: a working file or directory named
    <act>.<name>.<pid>.<random> whose pid no process holds, and any other entry but a directory a
    command declares it keeps there."""
    if not root.is_dir():
        return []
    found: list[tuple[Path, str]] = []
    for entry in sorted(root.iterdir()):
        named = RUN_FILE.fullmatch(entry.name)
        if named:
            if not lives(int(named.group(1))):
                found.append((entry, facts.phrase('a working file whose run is gone')))
        elif not (entry.is_dir() and not entry.is_symlink() and entry.name in kept):
            found.append((entry, facts.phrase('no command keeps it')))
    return found


@dataclass
class Orphan:
    size: str
    why: str
    act: facts.Would | None = None


@dataclass
class Status:
    """Bare corpus-yoga tmp: the tier, each orphan by its path, and under now: the cleaner over
    what it would remove, by path - the shape the cache's and the logs' statuses have, so that
    the room's one reading, which folds this block, names a file a dead run left."""
    tmp: str = facts.named('tmp')
    entries: dict[str, str] | None = None         # each directly under tmp/, by name: its size
    orphans: dict[str, Orphan] | None = None
    now: dict | str | None = None


def status_facts() -> Status:
    root = tier.TMP
    if not root.is_dir():
        return Status(facts.phrase('absent - no run has kept a working file'), None, {}, facts.phrase('none - nothing to do'))
    found = {rel: Orphan(human(size_of(p)), why, facts.Would(spell.line('tmp', 'clean'), {rel: 1}))
             for p, why in orphans(root, keepers()) for rel in (p.relative_to(REPO).as_posix() if p.is_relative_to(REPO) else str(p),)}
    held = {e.name: human(size_of(e)) for e in sorted(root.iterdir())}
    said = (facts.phrase('{n} entry(ies), {size}, {orphans} orphan(s)', n=len(held), size=human(size_of(root)), orphans=len(found)) if found
            else facts.phrase('{n} entry(ies), {size}', n=len(held), size=human(size_of(root))))
    out = Status(said, held or None, found)
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
    return [cleaner.Entry('orphan', rel, {'orphan': why, 'size': human(size_of(p))}, lambda p=p: _dispose(p), rel)
            for p, why in orphans(tier.TMP, keepers()) for rel in (p.relative_to(REPO).as_posix() if p.is_relative_to(REPO) else str(p),)]


def main() -> int:
    args = command_parser('tmp').parse_args()
    if args.verb == 'clean':
        return cleaner.clean('tmp', entries(), KINDS)
    facts.say(status_facts())
    return 0


if __name__ == '__main__':
    sys.exit(main())
