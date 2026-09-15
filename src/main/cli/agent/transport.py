#!/usr/bin/env python
"""
transport.py - the transport contract every provider's harness adapter keeps,
and the append-only placement the adapters share (#633).

A harness is the program a provider ships to let its model act as a coding
agent - Claude Code for claude, Antigravity for gemini - and each keeps a live
session store of its own shape, mounted at ext/mnt/agent/<provider> (#636).
The adapter for a provider lives at src/main/cli/agent/<provider>/harness.py,
by function with provider subdirectories as the browser capture is laid out
(#626), and exposes four functions the driver (agent.py) calls without knowing
the store's shape:

    live_sessions(mount)              every session the live store holds
    held_sessions(machine_dir)        every session one machine's store dir holds
    capture(mount, outbox, uuid8)     mirror one session (uuid8) or every session
                                      (uuid8 None) into the outbox; the conflict count
    model_rows(mount)                 (project, session, model, records) per session

The registry (rsc/provider/providers.csv) declares a provider; the adapter's
presence says the agent verb serves it. The store a provider's sessions are
transported to is data/input/<provider>/code/machine-transport/<machine>/<project>/,
the project key being Claude Code's encoding of the workspace path, so one
workspace lands under one name in every provider's store.
"""
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

SELF = 'src/main/cli/agent/transport.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
from append_only import Relation, growth, may_replace, relate  # noqa: E402

AGENT_DIR = REPO / 'src' / 'main' / 'cli' / 'agent'


@dataclass
class Session:
    provider: str
    id: str        # the harness's own session id
    project: str   # the store's project key (see project_key)
    path: Path     # the session's record in the store it was read from
    title: str
    size: int      # bytes the record occupies
    mtime: float   # the record's last write


def project_key(workspace: str) -> str:
    """Claude Code's encoding of a workspace path - every character outside
    [A-Za-z0-9] becomes '-' - so one workspace reads the same in every
    provider's store."""
    return ''.join(c if c.isalnum() else '-' for c in workspace)


def store(provider: str) -> Path:
    return REPO / 'data' / 'input' / provider / 'code' / 'machine-transport'


def ambiguous(prefix: str, matches: list[tuple[str, str]], provider: str) -> str:
    """The refusal when a uuid prefix names more than one record: each match with
    its project, since one session can sit under two projects (a fork a repository
    rename leaves), and the act that takes them all - the provider's totality -
    because --id names one session and here there are several records of one."""
    return (f'error: {prefix!r} names {len(matches)} records: '
            + ', '.join(f'{project}/{sid}' for project, sid in matches)
            + f' - --id names one session; to capture every record, take the provider\'s totality: --provider {provider}')


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


def word_placement(relation: Relation, detail: str, src: str, dest: str) -> str:
    """One lattice state as one sentence, both sides NAMED — noun extends noun
    (user specification, 2026-07-11): the opposition is local/remote, never a
    pronoun without an antecedent, never a metonym. A machine name is an ADDRESS
    (which remote), not a side — both sides of a transport belong to the same
    machine, so the name lives in the header/tail, not in the relation."""
    return {
        Relation.ABSENT:    f'nothing in {dest} yet — written',
        Relation.IDENTICAL: f'{src} and {dest} hold identical bytes — no-op',
        Relation.EXTENDS:   f'{src} extends {dest} ({detail}) — {dest} copy superseded',
        Relation.AHEAD:     f'{dest} is ahead of {src} — no-op',
        Relation.DIVERGED:  f'✗ CONFLICT: {src} and {dest} diverged — {dest} copy left in place',
    }[relation]


def move_workspace(src_ws: Path, dest_ws: Path, apply: bool,
                   src_label: str, dest_label: str) -> tuple[int, bool, bool]:
    """The session's eponymous workspace (subagent transcripts, persisted
    tool-results — files the session log REFERENCES) rides along. The
    filesystem, checked here and now, is the only oracle — no reconstruction
    of what "ever existed": a destination folder that is absent takes the
    workspace wholesale as a unit; one that is present (however it came to be)
    merges with log semantics per file — new / identical / prefix-superseded;
    divergence a loud CONFLICT, worded with both sides named (src_label /
    dest_label). Returns (conflicts, wrote, eventful): wrote is
    bytes-changed-at-destination; eventful adds anything else worth eyes
    (ahead files, conflicts) — L1 silence is neither."""
    if not src_ws.is_dir():
        return 0, False, False
    files = sorted(p for p in src_ws.rglob('*') if p.is_file() and p.name != '.DS_Store')
    if not dest_ws.exists():
        print(f'  workspace {src_ws.name}/: nothing in {dest_label} yet — '
              f'written whole ({len(files)} file(s))')
        if apply:
            for f in files:
                dest = dest_ws / f.relative_to(src_ws)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(f.read_bytes())
        return 0, True, True
    tally = {r: 0 for r in Relation}
    conflicts = 0
    for f in files:
        rel = f.relative_to(src_ws)
        relation, detail = place_log(f.read_bytes(), dest_ws / rel, apply)
        if relation is Relation.DIVERGED:
            print(f'  workspace/{rel}: {word_placement(relation, detail, src_label, dest_label)}')
            conflicts += 1
        else:
            tally[relation] += 1
    print(f'  workspace {src_ws.name}/: '
          + ', '.join(f'{n} {k}' for k, n in tally.items() if n)
          + (f', {conflicts} CONFLICT(S)' if conflicts else '')
          if any(tally.values()) or conflicts else
          f'  workspace {src_ws.name}/: empty')
    wrote = bool(tally[Relation.ABSENT] or tally[Relation.EXTENDS])
    return conflicts, wrote, wrote or bool(conflicts or tally[Relation.AHEAD])
