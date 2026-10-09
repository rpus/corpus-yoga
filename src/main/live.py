"""
live.py - the live stores this room mounts, read against a tier (#842): every session and
second-selection unit of each mounted store - ext/mnt/agent/<provider>, where the
provider's harness writes - related to the copy a tier holds of it by the measure the
pipeline declares for its kind, the one promotion relates by, so that no two readings can
disagree. The stage reads them against itself, since a capture writes the stage and that
is the tier the live stores feed; nothing reads them against the store, which the stage
feeds. Reads the live stores and the tier; writes nothing.
"""
import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/live.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'agent'))   # the harness adapters: what a live store holds
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
        if store.provider != name or not str(store.input).endswith('code/machine-transport'):
            continue
        for extra in store.globs[1:]:
            for found in sorted(mount.glob(extra.pattern.split('/', 1)[1].rstrip('/'))):
                if found.is_dir() == extra.pattern.endswith('/'):
                    out.append((extra.kind, found))
    return out


@dataclass
class Ahead:
    """One live thing against the tier's copy of it: what the readers of the reading are
    given - the status, and any verb that would act on what is ahead."""
    provider: str
    kind: str                 # what its selection's declaration calls it
    name: str                 # a session's id, a memory's project
    state: str                # new, grown, changed, level, behind or diverged
    live: str                 # the live side, in words
    copy: str                 # the tier's side, in words; empty where the tier holds nothing
    tier: str = 'staged'      # what the tier's side is called: staged, or held
    agree: int = 0            # for a diverged session, the bytes the two agree on before they part
    link: str = ''            # the project whose directory this one is a link to
    capture: str = ''         # the capture, by extent, that stages exactly this; empty where a session's capture brings it

    @property
    def key(self) -> str:
        """What the live thing is called: its provider, its kind, its name."""
        return f'{self.provider} {self.kind} {self.name}'

    def facts(self) -> dict:
        """The live thing as the status states it: its state, both sides, and what stages it."""
        staged_by: facts.Command | facts.Act | None = None
        if self.capture:
            staged_by = facts.Command(self.capture, 'would stage it')
        elif self.kind != 'session' and self.state in ('new', 'changed'):
            staged_by = facts.Act('with a session of its project')
        then = {'diverged': 'a capture of it would be refused at promotion; the reader reconciles the two',
                'behind': f'the {self.tier} copy holds more than the live store does'}.get(self.state)
        return {'state': self.state, 'live': self.live, self.tier: self.copy or None,
                'agree for': f'{self.agree} bytes' if self.state == 'diverged' else None,
                'then': then, 'link to': self.link or None, 'capture': staged_by}


@dataclass
class AbsentMount:
    """A live store this room does not mount: nothing is read there."""
    state: str = 'absent'
    why: str = 'no live store is read there'
    remedy: facts.Command = facts.Command('corpus-yoga agent mount --apply', 'would mount it')


def _logs(path: Path, pattern: str) -> dict[str, bytes]:
    """The files a session's measure reads, by name: the session's own file, or under its
    directory the files its pipeline's glob names, wherever the harness keeps them."""
    if path.is_file():
        return {path.name: path.read_bytes()}
    found = sorted(path.glob(pattern)) or sorted(path.rglob(pattern))
    return {f.name: f.read_bytes() for f in found if f.is_file()}


STATE = {corpus.Relation.ABSENT: 'new', corpus.Relation.IDENTICAL: 'level', corpus.Relation.EXTENDS: 'grown',
         corpus.Relation.AHEAD: 'behind', corpus.Relation.DIVERGED: 'diverged'}


def live_addresses() -> tuple[frozenset[Path], frozenset[Path]]:
    """The store addresses this room's live stores still write - each live session's, each
    live second-selection unit's, what a capture of this room would renew - and among them
    the newest: a live directory that is a link, since a link is made from the newer to the
    older (the maintainer, reading-room 2026-10-02), so that of an identical pair the store
    keeps the copy under the newer name (#744)."""
    room = registry.machine()
    live: set[Path] = set()
    newest: set[Path] = set()
    for row in registry.providers():
        name = row['provider']
        mount, adapter = registry.mount(row), transport.adapter(name)
        if mount is None or adapter is None or not mount.is_dir():
            continue
        under = transport.store(name).relative_to(corpus.STORE) / room
        for s in adapter.live_sessions(mount):
            live.add(under / s.project / s.path.name)
        for _kind, path in _live_extras(name, mount):
            address = under / path.parent.name / path.name
            live.add(address)
            if path.is_symlink():
                newest.add(address)
    return frozenset(live), frozenset(newest)


def ahead(root: Path) -> tuple[list[Ahead], list[str]]:
    """The live stores against the tier under root - tmp/stage/input, or data/input - as
    rows: every session and second-selection unit of each live store this room mounts,
    related to the tier's copy by the measure the pipeline declares for its kind, and the
    mounts that are absent, by path."""
    room = registry.machine()
    tier = 'held' if root == corpus.STORE else 'staged'
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
        copy_dir = root / transport.store(name).relative_to(corpus.STORE) / room
        declared = next(s for s in corpus.stores() if s.pipeline == 'code-transport' and s.provider == name)
        glob, measure, kind = declared.globs[0].pattern, declared.globs[0].measure, declared.globs[0].kind
        _value, leq, _words = corpus.MEASURE[measure]
        pattern = glob.rsplit('/', 1)[-1]
        copies: dict[str, list] = {}
        for s in (adapter.held_sessions(copy_dir) if copy_dir.is_dir() else []):
            copies.setdefault(s.id, []).append(s)
        for s in adapter.live_sessions(mount):
            capture = f'corpus-yoga agent capture --provider {name} --id {s.id[:8]}'
            # the tier's copy at the session's own address, else the fullest copy under another name
            copy = next((c for c in copies.get(s.id, []) if c.project == s.project),
                        max(copies.get(s.id, []), key=lambda c: c.size, default=None))
            live_logs = _logs(s.path, pattern)
            copy_logs = _logs(copy.path, pattern) if copy is not None else None
            state = STATE[corpus.derive(live_logs, copy_logs, leq)]
            agree = 0
            if state == 'diverged' and copy_logs is not None:
                for key, mine in live_logs.items():
                    theirs = copy_logs.get(key, b'')
                    agree = next((i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b), min(len(mine), len(theirs)))
                    break
            rows.append(Ahead(name, kind, s.id[:8], state, corpus.human(s.size),
                              '' if copy is None else corpus.human(copy.size), tier, agree=agree,
                              capture=capture if state in ('new', 'grown') else ''))
        for kind, path in _live_extras(name, mount):
            project = path.parent.name
            link = path.resolve().parent.name if path.is_symlink() else ''
            copy_dir_of = copy_dir / project / path.name
            live_tree = _tree(path)
            if not copy_dir_of.is_dir():
                rows.append(Ahead(name, kind, project, 'new', f'{len(live_tree)} file(s)', '', tier, link=link))
                continue
            copy_tree = _tree(copy_dir_of)
            differ = sum(1 for k in set(live_tree) | set(copy_tree) if live_tree.get(k) != copy_tree.get(k))
            rows.append(Ahead(name, kind, project, 'changed' if differ else 'level', f'{len(live_tree)} file(s)',
                              f'{differ} differ' if differ else 'the same', tier, link=link))
    return rows, absent


def ahead_facts(rows: list[Ahead], absent: list[str]) -> tuple[dict[str, Ahead | AbsentMount], int, int]:
    """The reading as facts: the absent mounts, by path, then each live thing that is not
    level with the tier's copy, by what it is called; returns (the items, ahead, level)."""
    items: dict[str, Ahead | AbsentMount] = {m: AbsentMount() for m in absent}
    items.update({r.key: r for r in rows if r.state != 'level'})
    found = sum(1 for r in rows if r.state in ('new', 'grown', 'changed', 'diverged'))
    return items, found, sum(1 for r in rows if r.state == 'level')


def captures(out: dict[str, dict[str, dict[str, int]]], rows: list[Ahead]) -> None:
    """Into a next: block, each live thing ahead of the tier's copy under the capture, by
    provider, that would stage it, keyed by the selection it is counted under."""
    for row in rows:
        if row.state in ('new', 'grown', 'changed', 'diverged'):
            key = corpus.selection_of('code-transport', row.provider, row.kind) or f'{row.provider} {row.kind}'
            corpus.step(out, f'corpus-yoga agent capture --provider {row.provider}', key)
