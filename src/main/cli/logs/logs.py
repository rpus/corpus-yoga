#!/usr/bin/env python
"""
logs.py (corpus-yoga logs) - the room's logs, tmp/logs, as the cache and the stage have
their nouns (#814).

    corpus-yoga logs                    # status: the tier, each orphaned directory, and what to run next
    corpus-yoga logs clean              # remove the orphaned directories the status names

The tier is laid out by the dispatcher (src/main/cli/cli.py): tmp/logs/<command>/ holds
the bare command's logs, tmp/logs/<command>/<verb>/ each verb's, one stamped log per act -
the launcher's tee of the whole verb, the one record (#708) - beside which a verb keeps
the artifacts it names by the same stamp: the gate's <stamp>.report, a capture's
<stamp>.<provider>.progress, a daemon's <stamp>.daemon.
A directory is an orphan where its command has no declaration under src/main/cli, or its
verb none beside its command's - the log directory of a command or verb that no longer
exists, which nothing writes and no status read. The status names each with its count and
size; the cleaner, which takes no flag, removes them through the one loop every clean verb
runs (src/main/cleaner.py). A current command's logs are never the cleaner's: a log is the
record of an act.
"""
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/logs/logs.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main'))
from declared_parser import command_parser  # noqa: E402
import cleaner  # noqa: E402 - the one loop every clean verb runs (#837)
import corpus  # noqa: E402 - the room's to-do, which every act ends on (#875)
import facts  # noqa: E402
import tier  # noqa: E402

LOGS = tier.TMP / 'logs'
CLI = REPO / 'src' / 'main' / 'cli'
KINDS = {'orphan': 'orphans'}


def size_of(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())


def human(n: float) -> str:
    for unit in ('B', 'K', 'M'):
        if n < 1024:
            return f'{n:.0f}{unit}' if unit == 'B' else f'{n:.1f}{unit}'
        n /= 1024
    return f'{n:.1f}G'


def logs_in(path: Path) -> int:
    return sum(1 for f in path.rglob('*.log')) if path.is_dir() else (1 if path.suffix == '.log' else 0)


def orphans() -> list[tuple[Path, str]]:
    """Each entry under tmp/logs that no current command or verb writes: a directory of a
    command with no declaration under src/main/cli, a verb's directory with no declaration
    beside its command's, a file where only a command's directory belongs, or a directory
    beneath a verb's - a verb keeps files beside its record, never a directory (#708), so
    the per-provider directories the browser capture once wrote are named here; with why."""
    out: list[tuple[Path, str]] = []
    if not LOGS.is_dir():
        return out
    for command in sorted(LOGS.iterdir()):
        if command.name == '.DS_Store':
            out.append((command, 'no command keeps it'))
            continue
        if not command.is_dir():
            out.append((command, 'no command keeps a log here'))
            continue
        if not (CLI / command.name / f'{command.name}.json').is_file():
            out.append((command, f'no command corpus-yoga {command.name}'))
            continue
        for verb in sorted(command.iterdir()):
            if verb.is_dir() and not (CLI / command.name / f'{verb.name}.json').is_file():
                out.append((verb, f'no verb corpus-yoga {command.name} {verb.name}'))
                continue
            if verb.is_dir():
                for entry in sorted(verb.iterdir()):
                    if entry.is_dir():
                        out.append((entry, f'a directory beneath a verb\'s: corpus-yoga {command.name} {verb.name} keeps files beside its record, never a directory'))
    return out


@dataclass
class Tier:
    commands: int
    logs: int
    size: str


@dataclass
class Orphan:
    logs: int
    size: str
    why: str
    remedy: facts.Command = facts.Command('corpus-yoga logs clean', 'would remove it')


@dataclass
class Status:
    """Bare corpus-yoga logs: the tier, each orphan by its path, and under next: the cleaner
    over what it would remove, by path - the shape the cache's and the store's statuses
    have, so that bare status, which grafts next:, names an orphaned log directory."""
    tmp_logs: Tier | str = facts.named('tmp/logs')
    orphans: dict[str, Orphan] | None = None
    next: dict[str, dict[str, dict[str, int]]] | str | None = None
    logs: str = ''                # the verdict


def status_facts() -> Status:
    if not LOGS.is_dir():
        return Status('absent - no act has been logged', {}, 'none - nothing to do', 'no logs')
    commands = [d for d in LOGS.iterdir() if d.is_dir()]
    found = {p.relative_to(REPO).as_posix(): Orphan(logs_in(p), human(size_of(p)), why) for p, why in orphans()}
    return Status(Tier(len(commands), logs_in(LOGS), human(size_of(LOGS))), found,
                  {'corpus-yoga logs clean': {'would remove': {rel: 1 for rel in found}}} if found else 'none - nothing to do',
                  f'{len(commands)} command(s), {logs_in(LOGS)} log(s)' + (f', {len(found)} orphan(s)' if found else ''))


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
    """Everything the janitor acts on: each orphan by its path, with its count, size and why."""
    return [cleaner.Entry('orphan', p.relative_to(REPO).as_posix(),
                          {'orphan': why, 'logs': logs_in(p), 'size': human(size_of(p))},
                          lambda p=p: _dispose(p), p.relative_to(REPO).as_posix())
            for p, why in orphans()]


def main() -> int:
    args = command_parser('logs').parse_args()
    if args.verb == 'clean':
        return cleaner.clean('logs', entries(), KINDS, lambda: {**corpus.room_next(), **(own if isinstance(own := status_facts().next, dict) else {})})
    facts.say(status_facts())
    return 0


if __name__ == '__main__':
    sys.exit(main())
