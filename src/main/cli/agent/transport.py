#!/usr/bin/env python
"""
transport.py - the transport contract every provider's harness adapter keeps,
and the append-only placement the adapters share (#633).

A harness is the program a provider ships to let its model act as a coding
agent - Claude Code for claude, Antigravity for gemini - and each keeps a live
session store of its own shape, mounted at ext/mnt/<provider>/code/machine-transport/<machine>
(#636, #853), the address its units have under tmp/stage/input and data/input, so that
ext/mnt, tmp/stage/input and data/input are three roots over one address grammar.
The adapter for a provider lives at src/main/cli/agent/<provider>/harness.py,
by function with provider subdirectories as the browser capture is laid out
(#626), and exposes four functions the driver (agent.py) calls without knowing
the store's shape:

    live_sessions(mount)              every session the live store holds
    held_sessions(machine_dir)        every session one machine's store dir holds
    capture(mount, outbox, held, uuid8)
                                      mirror one session (uuid8) or every session
                                      (uuid8 None) into the outbox, the stage, against
                                      the staged copy where there is one, else the held
                                      one under held (#850); the conflict count
    model_rows(mount)                 (project, session, model, records) per session

The registry (rsc/provider/providers.csv) declares a provider; the adapter's
presence says the agent verb serves it. The store a provider's sessions are
transported to is data/input/<provider>/code/machine-transport/<machine>/<project>/,
the project key being Claude Code's encoding of the workspace path, so one
workspace lands under one name in every provider's store.
"""
from collections.abc import Iterator
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

SELF = 'src/main/cli/agent/transport.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import tier  # noqa: E402 — the tiers, one home (#702)
import provider as registry  # noqa: E402 - the live tier's root and the transport address (#853)
import cleaner  # noqa: E402 - the count a verdict says a kind by (#857)
from append_only import Relation, growth, may_replace, relate  # noqa: E402

AGENT_DIR = REPO / 'src' / 'main' / 'cli' / 'agent'
# The three roots a unit's one address is read under, as the narration names them (#854):
# the live tier, the stage, the store.
LIVE = registry.MOUNT_ROOT.relative_to(REPO).as_posix()
STAGE = tier.TMP_STAGE_INPUT.relative_to(REPO).as_posix()
STORE = (tier.DATA / 'input').relative_to(tier.DATA_ROOT).as_posix()


def under(outbox: Path) -> Path:
    """The address of an outbox's units under every root: the outbox under the stage."""
    return outbox.relative_to(tier.TMP_STAGE_INPUT)


@dataclass
class Session:
    provider: str
    id: str        # the harness's own session id
    project: str   # the store's project key (see project_key)
    path: Path     # the session's record in the store it was read from
    title: str
    size: int      # bytes the record occupies
    mtime: float   # the record's last write


def strings(value: object) -> Iterator[str]:
    """Every string a tool call's input holds, at any depth, in order."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def project_key(workspace: str) -> str:
    """Claude Code's encoding of a workspace path - every character outside
    [A-Za-z0-9] becomes '-' - so one workspace reads the same in every
    provider's store."""
    return ''.join(c if c.isalnum() else '-' for c in workspace)


def store(provider: str) -> Path:
    return tier.DATA / 'input' / provider / registry.TRANSPORT


def adapter(provider: str) -> ModuleType | None:
    """The provider's harness adapter, or None where none exists: the agent verb
    serves exactly the providers with one."""
    path = AGENT_DIR / provider / 'harness.py'
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f'{provider}_harness', path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def place_log(data: bytes, dest: Path, apply: bool) -> tuple[Relation, str]:
    """Append-only placement: the relation decides, this writes. A destination
    the incoming stream extends is superseded in place (the fast-forward); a
    destination already ahead is never truncated, so replaying an old transport
    is idempotent; divergence writes nothing and is the caller's to voice."""
    existing = dest.read_bytes() if dest.exists() else None
    relation = relate(data, existing)
    if apply and may_replace(relation):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    had, now = growth(data, existing)
    return relation, f'{had} → {now} bytes' if relation is Relation.EXTENDS else ''


PLURAL = {'session': 'sessions', 'memory': 'memories', 'file': 'files'}   # the kinds a verdict counts


def agreement(a: bytes, b: bytes | None) -> int:
    """How many bytes two streams agree on before they part."""
    b = b or b''
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


def fact(relation: Relation, data: bytes, existing: bytes | None, src: str, dest: str) -> dict[str, str]:
    """One lattice state as one fact (#854, #857): the relation as a whole-scalar key,
    both sides named by root - ext/mnt, tmp/stage/input or data/input - and its measure
    as the value. The unit's address is the fact's header, so the key carries roots alone."""
    had, now = growth(data, existing)
    return {
        Relation.ABSENT:    {f'{dest} holds nothing yet': f'{now} bytes'},
        Relation.IDENTICAL: {f'{src} and {dest} hold identical bytes': f'{now} bytes'},
        Relation.EXTENDS:   {f'{src} extends {dest}': f'{had} → {now} bytes'},
        Relation.AHEAD:     {f'{dest} is ahead of {src}': f'{had} > {now} bytes'},
        Relation.DIVERGED:  {f'{src} and {dest} diverged': f'agree for {agreement(data, existing)} bytes'},
    }[relation]


def outcome(relation: Relation) -> str:
    """What a placement under the relation did to the destination: wrote, kept, or conflict."""
    return 'wrote' if may_replace(relation) else 'conflict' if relation is Relation.DIVERGED else 'kept'


@dataclass
class Log:
    """One transport's facts, nested by outcome (#857), as the cleaners' and the
    promote's logs are: under each outcome - what the act did, or would do, to the root it
    writes - every unit it touched by its address, and beneath the unit the relation that
    decided it. A unit appears once, under the one thing that happened to it; the verdict
    counts each outcome by kind."""
    dest: str                        # the root the act writes: STAGE for a capture, LIVE for an install
    tense: str = 'did'               # did, or would for a dry run
    by: dict[str, dict[str, object]] = field(default_factory=dict)      # outcome → address → the unit's facts
    counted: dict[tuple[str, str], int] = field(default_factory=dict)  # (outcome, kind) → how many

    CONFLICT = '✗ CONFLICT'

    def key(self, which: str) -> str:
        """The outcome's key: wrote, kept or conflict as the log says it."""
        return {'wrote': f'{self.tense} write to {self.dest}', 'kept': f'{self.tense} NOT write', 'conflict': self.CONFLICT}[which]

    def say(self, which: str, address: str, facts: object, kind: str | None = None) -> None:
        """One unit under its outcome; kind counts it toward the verdict."""
        self.by.setdefault(self.key(which), {})[address] = facts
        if kind:
            self.counted[(which, kind)] = self.counted.get((which, kind), 0) + 1

    @property
    def conflicts(self) -> int:
        return len(self.by.get(self.CONFLICT, {}))

    def facts(self) -> dict[str, object]:
        """The outcomes in the workflow's order: written, kept, conflicted."""
        return {self.key(which): self.by[self.key(which)] for which in ('wrote', 'kept', 'conflict') if self.key(which) in self.by}


def verdict(act: str, logs: list[Log]) -> str:
    """The one line a transport ends on: DONE, or NOT DONE where any unit conflicted, then
    each outcome with how many of each kind - the auxiliary and the infinitive carrying
    the tense, as the cleaners' lines do."""
    counted: dict[tuple[str, str], int] = {}
    for log in logs:
        for key, n in log.counted.items():
            counted[key] = counted.get(key, 0) + n
    tense, dest = (logs[0].tense, logs[0].dest) if logs else ('did', '')
    clauses = []
    for which, words in (('wrote', f'{tense} write'), ('kept', f'{tense} NOT write'), ('conflict', Log.CONFLICT)):
        kinds = ', '.join(cleaner.count(counted[(which, kind)], kind, PLURAL) for kind in PLURAL if counted.get((which, kind)))
        if kinds:
            clauses.append(f'{words} {kinds}' + (f' to {dest}' if which == 'wrote' else ''))
    done = 'NOT DONE' if any(log.conflicts for log in logs) else 'DONE'
    return f'{act}: {done} - ' + ('; '.join(clauses) if clauses else 'nothing to transport')


def place_tree(src_ws: Path, dest_ws: Path, apply: bool, src: str, dest: str) -> tuple[str, dict[str, object]] | None:
    """A session's eponymous workspace (subagent transcripts, persisted tool-results -
    files the session log REFERENCES) rides along. The filesystem, checked here and now,
    is the only oracle: a destination folder that is absent takes the workspace wholesale
    as a unit; one that is present (however it came to be) merges with log semantics per
    file - new / identical / prefix-superseded, divergence a CONFLICT with the file named.
    Returns (outcome, facts), or None where the source has no workspace."""
    if not src_ws.is_dir():
        return None
    files = sorted(p for p in src_ws.rglob('*') if p.is_file() and p.name != '.DS_Store')
    if not dest_ws.exists():
        if apply:
            for f in files:
                target = dest_ws / f.relative_to(src_ws)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(f.read_bytes())
        return 'wrote', {f'{dest} holds nothing yet': f'{len(files)} file(s)'}
    tally = {r: 0 for r in Relation}
    facts: dict[str, object] = {}
    for f in files:
        rel = f.relative_to(src_ws)
        data = f.read_bytes()
        existing = (dest_ws / rel).read_bytes() if (dest_ws / rel).exists() else None
        relation = relate(data, existing)
        if apply and may_replace(relation):
            (dest_ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (dest_ws / rel).write_bytes(data)
        tally[relation] += 1
        if relation is Relation.DIVERGED:
            facts[rel.as_posix()] = fact(relation, data, existing, src, dest)
    words = {Relation.ABSENT: 'new', Relation.IDENTICAL: 'identical', Relation.EXTENDS: 'superseded',
             Relation.AHEAD: 'ahead', Relation.DIVERGED: 'diverged'}
    facts = {f'merged into {dest}': ', '.join(f'{n} {words[r]}' for r, n in tally.items() if n) or 'empty', **facts}
    which = 'conflict' if tally[Relation.DIVERGED] else 'wrote' if tally[Relation.ABSENT] or tally[Relation.EXTENDS] else 'kept'
    return which, facts
