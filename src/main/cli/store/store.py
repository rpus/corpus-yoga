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


def ahead() -> tuple[int, int]:
    """The lines of the third reading; returns (ahead, level)."""
    room = registry.machine()
    found = level = 0
    mounted = False
    for row in registry.providers():
        name = row['provider']
        mount, adapter = registry.mount(row), transport.adapter(name)
        if mount is None or adapter is None:
            continue
        if not mount.is_dir():
            print(f'  {mount.relative_to(REPO)}: absent - no live {name} store is read; '
                  'corpus-yoga prerequisites sync --apply mounts it')
            continue
        mounted = True
        held_dir = transport.store(name) / room
        held: dict[str, int] = {}
        for s in (adapter.held_sessions(held_dir) if held_dir.is_dir() else []):
            held[s.id] = max(held.get(s.id, 0), s.size)
        for s in adapter.live_sessions(mount):
            capture = f'corpus-yoga agent capture --provider {name} --id {s.id[:8]}'
            if s.id not in held:
                found += 1
                print(f'  {name} session {s.id[:8]}: {corpus.human(s.size)} live, not held - {capture}')
            elif s.size > held[s.id]:
                found += 1
                print(f'  {name} session {s.id[:8]}: {corpus.human(s.size)} live, {corpus.human(held[s.id])} held - {capture}')
            elif s.size < held[s.id]:
                print(f'  {name} session {s.id[:8]}: {corpus.human(s.size)} live, {corpus.human(held[s.id])} held - '
                      'the store holds more than the live store does')
            else:
                level += 1
        for kind, path in _live_extras(name, mount):
            project = path.parent.name
            link = (f'; a link to {path.resolve().parent.name}\'s, so one directory under two names'
                    if path.is_symlink() else '')
            held_copy = held_dir / project / path.name
            live_tree = _tree(path)
            if not held_copy.is_dir():
                found += 1
                print(f'  {name} {kind} of {project}: {len(live_tree)} file(s) live, not held{link} - '
                      'staged with a session of its project')
                continue
            held_tree = _tree(held_copy)
            differ = sorted(k for k in set(live_tree) | set(held_tree) if live_tree.get(k) != held_tree.get(k))
            if differ:
                found += 1
                print(f'  {name} {kind} of {project}: {len(differ)} of {len(live_tree)} file(s) differ from the held ones'
                      f'{link} - staged with a session of its project')
            else:
                level += 1
    if not mounted:
        print('  no live store is mounted in this workspace')
    return found, level


def main() -> int:
    command_parser('store').parse_args()
    held, twice = corpus.store_status()
    print('ahead - what this room\'s live stores hold that the store does not:')
    found, level = ahead()
    if not found:
        print(f'  nothing: {level} live unit(s) level with the held ones')
    print(f'store: {held} unit(s) held; {twice} held more than once; {found} ahead in this room\'s live stores'
          + (f', {level} level' if found else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
