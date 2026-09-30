#!/usr/bin/env python
"""
store.py (corpus-yoga store) - shared storage, data/input, as the stage has its noun (#738).

    corpus-yoga store    # status: the units held, what is held more than once, what this room's live stores hold beyond it

The store read in the stage's terms (src/main/corpus.py): a unit is what a pipeline's
declaration selects, at an address. Three readings, and nothing written:

  held        the units by pipeline, provider and kind, and any file no pipeline selects
              and no capturing noun writes;
  held twice  every unit whose content another unit of its kind holds whole - identical,
              or contained by the measure its pipeline declares - with the unit that
              holds it: one thing at several addresses;
  ahead       for each live store this room mounts, what it holds that the store does
              not - a session new or grown, a memory changed - with the capture, by
              extent, that stages exactly that.

The third is a status's to say and never a capture's: a capture reads no capture (L10),
so it cannot know what is held, and stages all its source holds; a status may relate the
live store to the held one, and the reader captures by the extent it names.
"""
import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/store/store.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'src' / 'main'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'agent'))   # the harness adapters: what a live store holds
from declared_parser import command_parser  # noqa: E402
import corpus  # noqa: E402
import provider as registry  # noqa: E402

transport = importlib.import_module('transport')   # src/main/cli/agent/transport.py, by the path inserted above


def _tree(path: Path) -> dict[str, bytes]:
    return {f.relative_to(path).as_posix(): f.read_bytes()
            for f in sorted(path.rglob('*')) if f.is_file() and f.name != '.DS_Store'}


def _live_extras(name: str, mount: Path) -> list[tuple[str, Path]]:
    """What the provider's second selection finds in a live store: (kind, path). The
    declaration's glob is over <machine>/<project>/...; a live store is one machine's, so
    the glob without its first segment is the glob over the mount."""
    out = []
    for store in corpus.stores():
        if store['provider'] != name or not str(store['input']).endswith('code/machine-transport'):
            continue
        for glob, _measure, kind in store['globs'][1:]:
            for found in sorted(mount.glob(glob.split('/', 1)[1].rstrip('/'))):
                if found.is_dir() == glob.endswith('/'):
                    out.append((kind, found))
    return out


@dataclass
class Ahead:
    """One live thing against the held one of this room: what the readers of the third
    reading are given - the status below, and any verb that would act on what is ahead."""
    provider: str
    kind: str                 # what its selection's declaration calls it
    name: str                 # a session's id, a memory's project
    state: str                # new, grown, changed, level or behind
    live: str                 # the live side, in words
    held: str                 # the held side, in words; empty where nothing is held
    link: str = ''            # the project whose directory this one is a link to
    capture: str = ''         # the capture, by extent, that stages exactly this; empty where a session's capture brings it


def ahead() -> tuple[list[Ahead], list[str]]:
    """The third reading, as rows: every session and second-selection unit of each live
    store this room mounts, against the held one - and the mounts that are absent, by
    path. Reads the live stores and the store; writes nothing."""
    room = registry.machine()
    rows: list[Ahead] = []
    absent: list[str] = []
    for row in registry.providers():
        name = row['provider']
        mount, adapter = registry.mount(row), transport.adapter(name)
        if mount is None or adapter is None:
            continue
        if not mount.is_dir():
            absent.append(mount.relative_to(REPO).as_posix())
            continue
        held_dir = transport.store(name) / room
        held: dict[str, int] = {}
        for s in (adapter.held_sessions(held_dir) if held_dir.is_dir() else []):
            held[s.id] = max(held.get(s.id, 0), s.size)
        for s in adapter.live_sessions(mount):
            capture = f'corpus-yoga agent capture --provider {name} --id {s.id[:8]}'
            size = held.get(s.id)
            state = 'new' if size is None else 'grown' if s.size > size else 'behind' if s.size < size else 'level'
            rows.append(Ahead(name, 'session', s.id[:8], state, corpus.human(s.size),
                              '' if size is None else corpus.human(size),
                              capture=capture if state in ('new', 'grown') else ''))
        for kind, path in _live_extras(name, mount):
            project = path.parent.name
            link = path.resolve().parent.name if path.is_symlink() else ''
            held_copy = held_dir / project / path.name
            live_tree = _tree(path)
            if not held_copy.is_dir():
                rows.append(Ahead(name, kind, project, 'new', f'{len(live_tree)} file(s)', '', link))
                continue
            held_tree = _tree(held_copy)
            differ = sum(1 for k in set(live_tree) | set(held_tree) if live_tree.get(k) != held_tree.get(k))
            rows.append(Ahead(name, kind, project, 'changed' if differ else 'level', f'{len(live_tree)} file(s)',
                              f'{differ} differ' if differ else 'the same', link))
    return rows, absent


def say(rows: list[Ahead], absent: list[str]) -> tuple[int, int]:
    """The third reading's lines, from its rows; returns (ahead, level)."""
    for mount in absent:
        print(f'  {mount}: absent - no live store is read there; corpus-yoga prerequisites sync --apply mounts it')
    found = [r for r in rows if r.state in ('new', 'grown', 'changed')]
    for r in rows:
        link = f'; a link to {r.link}\'s, so one directory under two names' if r.link else ''
        if r.kind == 'session' and r.state in ('new', 'grown'):
            print(f'  {r.provider} session {r.name}: {r.live} live, {r.held + " held" if r.held else "not held"} - {r.capture}')
        elif r.kind == 'session' and r.state == 'behind':
            print(f'  {r.provider} session {r.name}: {r.live} live, {r.held} held - the store holds more than the live store does')
        elif r.state == 'new':
            print(f'  {r.provider} {r.kind} of {r.name}: {r.live} live, not held{link} - staged with a session of its project')
        elif r.state == 'changed':
            print(f'  {r.provider} {r.kind} of {r.name}: {r.held.split()[0]} of {r.live} differ from the held ones{link} - '
                  'staged with a session of its project')
    if not rows and not absent:
        print('  no live store is mounted in this workspace')
    return len(found), sum(1 for r in rows if r.state == 'level')


def main() -> int:
    command_parser('store').parse_args()
    held, twice = corpus.store_status()
    print('ahead - what this room\'s live stores hold that the store does not:')
    found, level = say(*ahead())
    if not found:
        print(f'  nothing: {level} live unit(s) level with the held ones')
    print(f'store: {held} unit(s) held; {twice} held more than once; {found} ahead in this room\'s live stores'
          + (f', {level} level' if found else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
