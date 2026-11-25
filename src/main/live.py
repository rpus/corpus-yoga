"""
live.py - the live stores this room mounts, read against the two tiers (issues/842, issues/851): every
session of each mounted store - ext/mnt/<provider>/code/machine-transport/<machine>,
a link to where the provider's harness writes, at the address its units have under the
other two roots (issues/853) - related to the fuller of the staged copy and the held copy
of it by the measure the pipeline declares for its kind, the one promotion relates by, so
that no two readings can disagree. A live thing the store holds level reads as level
however empty the stage is: the stage is a scratch tier between the live stores and the
store, and the store's status is where the reading is said. Reads the live stores and both
tiers; writes nothing.
"""
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import corpus
import facts
import spell
import provider as registry

SELF = 'src/main/live.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

transport = importlib.import_module('transport')   # src/main/cli/agent/transport.py, by the path inserted above

TIERS = {'staged': corpus.STAGED, 'held': corpus.HELD}   # what each tier's copy is called, and the tier's root


@dataclass
class Ahead:
    """One live thing against the fuller copy of it: what the readers of the reading are
    given - the status, and any verb that would act on what is ahead."""
    provider: str
    kind: str                 # what its selection's declaration calls it
    name: str                 # a session's id
    state: str                # new, grown, level, behind or diverged; or <room>'s, a session another room's store dir holds identical or ahead
    live: str                 # the live side, in words
    copy: str                 # the copy's side, in words; empty where neither tier holds one
    tier: str = 'staged'      # which tier's copy it was read against: staged, or held
    agree: int = 0            # for a diverged session, the bytes the two agree on before they part

    @property
    def key(self) -> str:
        """What the live thing is called: its provider, its kind, its name."""
        return f'{self.provider} {self.kind} {self.name}'

    def facts(self) -> dict:
        """The live thing as the status states it: its state, both sides, and the capture that
        stages it - the provider's, on the selection it is counted under (issues/1028)."""
        staged_by = None
        if self.state in ('new', 'grown', 'diverged'):
            key = corpus.selection_of('agent', self.provider, self.kind) or f'{self.provider} {self.kind}'
            staged_by = facts.Would(spell.line('agent', 'capture', provider=self.provider), {key: 1})
        then = {'diverged': facts.phrase('a capture of it would be refused at promotion; the reader reconciles the two'),
                'behind': facts.phrase('the {tier} copy holds more than the live store does', tier=self.tier)}.get(self.state)
        return {'state': self.state, 'live': self.live, self.tier: self.copy or None,
                'agree for': facts.phrase('{n} bytes', n=self.agree) if self.state == 'diverged' else None,
                'then': then, 'act': staged_by}


@dataclass
class AbsentMount:
    """A live store this room does not mount: nothing is read there."""
    state: str = 'absent'
    why: str = facts.phrase('no live store is read there')
    act: facts.Would | None = None


def _logs(path: Path, pattern: str) -> dict[str, bytes]:
    """The files a session's measure reads, by name: the session's own file, or under its
    directory the files the declaration's glob names below the unit - the same relative
    path under the live store and under each tier (issues/856)."""
    if path.is_file():
        return {path.name: path.read_bytes()}
    return {f.name: f.read_bytes() for f in sorted(path.glob(pattern)) if f.is_file()}


STATE = {corpus.Relation.ABSENT: 'new', corpus.Relation.IDENTICAL: 'level', corpus.Relation.EXTENDS: 'grown',
         corpus.Relation.AHEAD: 'behind', corpus.Relation.DIVERGED: 'diverged'}


def live_addresses() -> frozenset[Path]:
    """The store addresses this room's live stores still write - each live session's, what a
    capture of this room would renew."""
    room = registry.machine()
    live: set[Path] = set()
    for row in registry.providers():
        name = row['provider']
        mount, adapter = registry.mount(row), transport.adapter(name)
        if mount is None or adapter is None or not mount.is_dir():
            continue
        under = transport.store(name).relative_to(corpus.HELD) / room
        for s in adapter.live_sessions(mount):
            live.add(under / s.project / s.path.name)
    return frozenset(live)


def _copies(adapter: Any, roots: dict[str, Path]) -> dict[str, list[tuple[str, Any]]]:
    """Each tier's copies of a provider's sessions, by session id: (tier, the session, a
    transport.Session of the adapter's)."""
    copies: dict[str, list[tuple[str, Any]]] = {}
    for tier, root in roots.items():
        for s in (adapter.held_sessions(root) if root.is_dir() else []):
            copies.setdefault(s.id, []).append((tier, s))
    return copies


def _fuller(copies: list[tuple[str, Any]], project: str) -> tuple[str, Any] | None:
    """The copy a live session is read against: the fullest of both tiers' copies by size -
    under the prefix measure the fuller holds the other - the one at the session's own
    address first among equals."""
    if not copies:
        return None
    return max(copies, key=lambda pair: (pair[1].size, pair[1].project == project))


def sessions(name: str, adapter: Any, mount: Path, roots: dict[str, Path]) -> list[Ahead]:
    """Each live session of the provider's mount against the fuller of its copies under roots -
    each tier's directory of this room - by the measure the pipeline declares for its kind."""
    declared = next(s for s in corpus.stores() if s.pipeline == 'agent' and s.provider == name)
    glob, measure, kind = declared.globs[0].pattern, declared.globs[0].measure, declared.globs[0].kind
    _value, leq, _words = corpus.MEASURE[measure]
    pattern = '/'.join(glob.split('/')[declared.depth:])   # the glob below the unit: what a session directory holds of it
    copies = _copies(adapter, roots)
    rows: list[Ahead] = []
    for s in adapter.live_sessions(mount):
        found = _fuller(copies.get(s.id, []), s.project)
        tier, copy = found if found is not None else ('staged', None)
        live_logs = _logs(s.path, pattern)
        copy_logs = _logs(copy.path, pattern) if copy is not None else None
        state = STATE[corpus.derive(live_logs, copy_logs, leq)]
        peer = transport.held_by_peer(roots['held'], s.path.name, live_logs[s.path.name]) if s.path.is_file() and state in ('new', 'grown', 'diverged') else None
        if peer is not None:
            rows.append(Ahead(name, kind, s.id[:8], f"{peer[0]}'s", corpus.human(s.size), corpus.human(peer[1].stat().st_size), 'held'))
            continue
        agree = 0
        if state == 'diverged' and copy_logs is not None:
            for key, mine in live_logs.items():
                theirs = copy_logs.get(key, b'')
                agree = next((i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b), min(len(mine), len(theirs)))
                break
        rows.append(Ahead(name, kind, s.id[:8], state, corpus.human(s.size),
                          '' if copy is None else corpus.human(copy.size), tier, agree=agree))
    return rows


def ahead() -> tuple[list[Ahead], list[str]]:
    """The live stores against the two tiers, as rows: every session of each live store this
    room mounts, related to the fuller of the staged and the held copy by the measure the
    pipeline declares for its kind - a session another room's store dir holds identical or
    ahead is that room's, as the capture reads it - and the mounts that are absent, by path."""
    room = registry.machine()
    rows: list[Ahead] = []
    absent: list[str] = []
    for row in registry.providers():
        name = row['provider']
        mount, adapter = registry.mount(row), transport.adapter(name)
        if mount is None or adapter is None:
            continue
        if not mount.is_dir():
            live = registry.live_store(row)
            if live is not None and live.is_dir():   # mount links only a live store this machine holds
                absent.append(mount.relative_to(REPO).as_posix())
            continue
        under = transport.store(name).relative_to(corpus.HELD) / room
        roots = {tier: root / under for tier, root in TIERS.items()}
        rows.extend(sessions(name, adapter, mount, roots))
    return rows, absent


def ahead_facts(rows: list[Ahead], absent: list[str]) -> tuple[dict[str, Ahead | AbsentMount], int, int]:
    """The reading as facts: the absent mounts, by path, then each live thing that is not
    level with its copy, by what it is called; returns (the items, ahead, level)."""
    items: dict[str, Ahead | AbsentMount] = {m: AbsentMount(act=facts.Would(spell.line('agent', 'mount'), {m: 1})) for m in absent}
    items.update({r.key: r for r in rows if r.state != 'level'})
    found = sum(1 for r in rows if r.state in ('new', 'grown', 'changed', 'diverged'))
    return items, found, sum(1 for r in rows if r.state == 'level')
