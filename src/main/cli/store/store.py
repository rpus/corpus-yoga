#!/usr/bin/env python
"""
store.py (corpus-yoga store) - shared storage, data/input, as the stage has its noun (#738).

    corpus-yoga store                   # status: the units held, the duplicates, what this room's live stores hold beyond it
    corpus-yoga store clean --dry-run   # what the janitor would remove: each duplicate with what only it feeds, each orphaned shadow
    corpus-yoga store clean --apply     # remove it

The store read in the stage's terms (src/main/corpus.py): a unit is what a pipeline's
declaration selects, at an address. Three readings, and nothing written:

  held        the units by pipeline, provider and kind, and any file no pipeline selects
              and no capturing noun writes;
  duplicates  every unit whose content another unit of its kind holds - identical, the
              same at two addresses, or contained, whole within the other's by the measure
              its pipeline declares - with the unit that holds it;
  ahead       for each live store this room mounts, what it holds that the store does
              not - a session new, grown or diverged, a memory changed - related by the
              measure its pipeline declares, which is promotion's, with the capture, by
              extent, that stages exactly that.

The third is a status's to say and never a capture's: a capture reads no capture (L10),
so it cannot know what is held, and stages all its source holds; a status may relate the
live store to the held one, and the reader captures by the extent it names.

The janitor, store clean, acts on the second reading (#744): each duplicate, of either
species, goes with what only it feeds - its members, its record and its shadow under the
cache - and the holder stays; an orphaned shadow, the cache's derivation of a unit the
store no longer holds, goes too. Its lines keep their tenses - will remove before each
act, did or did NOT after - the status is re-read beneath them, and the verdict is the
last line, DONE only when every entry went; the dry run is the apply with the act elided.
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
import facts  # noqa: E402
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
    state: str                # new, grown, changed, level, behind or diverged
    live: str                 # the live side, in words
    held: str                 # the held side, in words; empty where nothing is held
    agree: int = 0            # for a diverged session, the bytes the two agree on before they part
    link: str = ''            # the project whose directory this one is a link to
    capture: str = ''         # the capture, by extent, that stages exactly this; empty where a session's capture brings it


def _logs(path: Path, pattern: str) -> dict[str, bytes]:
    """The files a session's measure reads, by name: the session's own file, or under its
    directory the files its pipeline's glob names, wherever the harness keeps them."""
    if path.is_file():
        return {path.name: path.read_bytes()}
    found = sorted(path.glob(pattern)) or sorted(path.rglob(pattern))
    return {f.name: f.read_bytes() for f in found if f.is_file()}


STATE = {corpus.Relation.ABSENT: 'new', corpus.Relation.IDENTICAL: 'level', corpus.Relation.EXTENDS: 'grown',
         corpus.Relation.AHEAD: 'behind', corpus.Relation.DIVERGED: 'diverged'}


def live_addresses() -> frozenset[Path]:
    """The store addresses this room's live stores still write: each live session's, each
    live second-selection unit's - what a capture of this room would renew, so the copy the
    store keeps of an identical pair is the one a capture keeps level (#744)."""
    room = registry.machine()
    out: set[Path] = set()
    for row in registry.providers():
        name = row['provider']
        mount, adapter = registry.mount(row), transport.adapter(name)
        if mount is None or adapter is None or not mount.is_dir():
            continue
        under = transport.store(name).relative_to(corpus.STORE) / room
        for s in adapter.live_sessions(mount):
            out.add(under / s.project / s.path.name)
        for _kind, path in _live_extras(name, mount):
            if not path.is_symlink():   # a link holds nothing: the directory it points to is the live one
                out.add(under / path.parent.name / path.name)
    return frozenset(out)


def ahead() -> tuple[list[Ahead], list[str]]:
    """The third reading, as rows: every session and second-selection unit of each live
    store this room mounts, against the held one, related by the measure the pipeline
    declares for its kind - the one promotion relates by, so the two readings cannot
    disagree - and the mounts that are absent, by path. Reads the live stores and the
    store; writes nothing."""
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
        declared = next(s for s in corpus.stores() if s['pipeline'] == 'code-transport' and s['provider'] == name)
        glob, measure, kind = declared['globs'][0]
        _value, leq, _words = corpus.MEASURE[measure]
        pattern = glob.rsplit('/', 1)[-1]
        copies: dict[str, list] = {}
        for s in (adapter.held_sessions(held_dir) if held_dir.is_dir() else []):
            copies.setdefault(s.id, []).append(s)
        for s in adapter.live_sessions(mount):
            capture = f'corpus-yoga agent capture --provider {name} --id {s.id[:8]}'
            # the held copy at the session's own address, else the fullest copy under another name
            held_copy = next((c for c in copies.get(s.id, []) if c.project == s.project),
                             max(copies.get(s.id, []), key=lambda c: c.size, default=None))
            live_logs = _logs(s.path, pattern)
            held_logs = _logs(held_copy.path, pattern) if held_copy is not None else None
            state = STATE[corpus.derive(live_logs, held_logs, leq)]
            agree = 0
            if state == 'diverged' and held_logs is not None:
                for key, mine in live_logs.items():
                    theirs = held_logs.get(key, b'')
                    agree = next((i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b), min(len(mine), len(theirs)))
                    break
            rows.append(Ahead(name, kind, s.id[:8], state, corpus.human(s.size),
                              '' if held_copy is None else corpus.human(held_copy.size), agree=agree,
                              capture=capture if state in ('new', 'grown') else ''))
        for kind, path in _live_extras(name, mount):
            project = path.parent.name
            link = path.resolve().parent.name if path.is_symlink() else ''
            held_copy = held_dir / project / path.name
            live_tree = _tree(path)
            if not held_copy.is_dir():
                rows.append(Ahead(name, kind, project, 'new', f'{len(live_tree)} file(s)', '', link=link))
                continue
            held_tree = _tree(held_copy)
            differ = sum(1 for k in set(live_tree) | set(held_tree) if live_tree.get(k) != held_tree.get(k))
            rows.append(Ahead(name, kind, project, 'changed' if differ else 'level', f'{len(live_tree)} file(s)',
                              f'{differ} differ' if differ else 'the same', link=link))
    return rows, absent


def ahead_facts(rows: list[Ahead], absent: list[str]) -> tuple[list, int, int]:
    """The third reading as facts: each live thing that is ahead as an item, with its state
    and what stages it; the absent mounts; returns (the items, ahead, level)."""
    items: list = [{'mount': m, 'state': 'absent', 'remedy': 'no live store is read there; corpus-yoga prerequisites sync --apply mounts it'}
                   for m in absent]
    for r in rows:
        if r.state == 'level':
            continue
        item: dict = {f'{r.provider} {r.kind}': r.name, 'state': r.state, 'live': r.live}
        if r.held:
            item['held'] = r.held
        if r.state == 'diverged':
            item['agree for'] = f'{r.agree} bytes'
            item['then'] = 'a capture of it would be refused at promotion; the reader reconciles the two'
        if r.state == 'behind':
            item['then'] = 'the store holds more than the live store does'
        if r.link:
            item['link to'] = r.link
        if r.capture:
            item['capture'] = r.capture
        elif r.kind != 'session' and r.state in ('new', 'changed'):
            item['capture'] = 'with a session of its project'
        items.append(item)
    found = sum(1 for r in rows if r.state in ('new', 'grown', 'changed', 'diverged'))
    return items, found, sum(1 for r in rows if r.state == 'level')


KINDS = {'duplicate': 'duplicates', 'orphaned shadow': 'orphaned shadows'}   # each kind of entry, and its plural


def _count(n: int, kind: str) -> str:
    return f'{n} {kind if n == 1 else KINDS[kind]}'


def _dispose_all(paths: list[Path]) -> str | None:
    for path in paths:
        why = corpus.dispose(path)
        if why is not None:
            return f'{path.relative_to(REPO) if path.is_relative_to(REPO) else path}: {why}'
    return None


def entries() -> list[tuple[str, dict, list[Path]]]:
    """Everything the janitor acts on, in the order it acts: (kind, the entry's facts, the
    paths that go). The one list both faces walk."""
    out: list[tuple[str, dict, list[Path]]] = []
    for unit, holder, how, by in corpus.held_twice(corpus.STORE, live_addresses()):
        paths = [corpus.STORE / m for m in unit.members + unit.record]
        own = corpus.shadow(unit)
        if own is not None and own.exists():
            paths.append(own)
        item = {unit.kind: unit.address.as_posix(), ('identical to' if how == 'identical' else 'contained by'): holder.address.as_posix(),
                'by': by, 'size': corpus.human(sum(corpus.size_of(p) for p in paths)),
                'goes': [p.relative_to(REPO).as_posix() if p.is_relative_to(REPO) else str(p) for p in paths]}
        out.append(('duplicate', item, paths))
    for d in corpus.orphaned_shadows():
        out.append(('orphaned shadow', {'shadow': d.relative_to(REPO).as_posix(), 'why': 'the store holds no unit it derives from',
                                         'size': corpus.human(corpus.size_of(d))}, [d]))
    return out


def clean(apply: bool) -> int:
    """One loop over the one list; the flag decides only whether the act runs after the lines."""
    rows = entries()
    did = {kind: 0 for kind in KINDS}
    left: list[str] = []
    print('would remove:' if not apply else 'will remove:' if rows else 'will remove: []')
    if not rows and not apply:
        print('  []')
    for kind, item, paths in rows:
        for line in facts.lines([item], 1):
            print(line)
        if not apply:
            did[kind] += 1
            continue
        why = _dispose_all(paths)
        if why is None:
            print('    did: removed')
            did[kind] += 1
        else:
            print(f'    did: NOT - {why}')
            left.append(f'{kind}: {why}')
    counts = ', '.join(_count(did[kind], kind) for kind in KINDS if did[kind]) or 'nothing'
    if not apply:
        print(f'store clean: would remove {counts}' + (' (--apply removes them)' if counts != 'nothing' else ''))
        return 0
    # the status over what remains is the certified state after the act: beneath the lines
    # and above the verdict, informing and never gating
    out, held, twice = corpus.store_facts(live_addresses())
    facts.say(out)
    if left:
        print(f'store clean: NOT DONE - removed {counts}; NOT removed ' + '; '.join(left))
    else:
        print(f'store clean: DONE - removed {counts}')
    return 1 if left else 0


def main() -> int:
    args = command_parser('store').parse_args()
    if args.verb == 'clean':
        return clean(bool(args.apply))
    out, held, twice = corpus.store_facts(live_addresses())
    rows, absent = ahead()
    items, found, level = ahead_facts(rows, absent)
    out['ahead'] = items if items else ('no live store is mounted in this workspace' if not rows else f'nothing: {level} live unit(s) level with the held ones')
    out['store'] = (f'{held} unit(s) held; {twice} duplicate(s); {found} ahead in this room\'s live stores'
                    + (f', {level} level' if found else ''))
    facts.say(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
