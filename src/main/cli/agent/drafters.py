#!/usr/bin/env python
"""
drafters.py (corpus-yoga agent list-drafters) - the Signatures on main, joined to the
sessions the store holds (#631).

A message on main ends in its Signatures, one line per hook run over it
(rsc/test/prepare-commit-msg-hook.sh, the grammar's one home): the first names who
DRAFTED it, each later one a co-drafter - a session or a room that amended, cherry-picked
or rebased it. The join holds two properties of the first, per provider:

  held     the session it names is a session the store holds
           (data/input/<provider>/code/machine-transport/<machine>/), or the corpus is
           behind and the room that ran the session is named, since only it can capture;
  written  the held session's own record carries the message - a tool call of that
           session, or of a subagent of it, wrote its words - so the claim is read from
           the corpus and never taken from the commit. A Signature typed by hand is held to the same
           reading as one the hook stamped.

A Signature naming a machine alone claims nothing of the drafter, and is counted as what
it is. The brief face, on the bare noun, reads held alone: it opens no session. Reads
git and the store; writes nothing.
"""
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/agent/drafters.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]

sys.path.insert(0, str(REPO / 'src' / 'main'))
sys.path.insert(0, str(REPO / 'src' / 'main' / 'cli' / 'agent'))
import provider as registry  # noqa: E402
import facts  # noqa: E402 - the one printer of a status's facts (#753)
import transport  # noqa: E402
from machine import bound_machine  # noqa: E402

REF = 'origin/main'
WINDOW = 60     # the letters and digits of a message that the record is searched for, at a time
REACH = 300     # how far into a message the windows are taken
JUDGEABLE = 25  # a message with fewer is too short to tell from another


def windows(text: str) -> list[str]:
    """What a record is searched for: the message's first line, its subject, and the
    message's letters in consecutive windows as far as REACH. A message is its session's
    when the record carries any one of them whole - the merge rewrites a word of the
    body's first clause (the PR template's enacting word), a single commit's subject is
    the squash's and not the body's, and neither moves the rest."""
    whole = letters(text)
    out = [letters(text.split('\n')[0])[:WINDOW]]
    out += [whole[i:i + WINDOW] for i in range(0, min(len(whole), REACH), WINDOW)]
    return [w for w in out if len(w) >= JUDGEABLE]


def letters(text: str) -> str:
    """A text as its letters and digits alone, lowercased: what survives a shell's quoting
    and a record's escaping unchanged, so a message reads the same in the commit and in
    the tool call that wrote it."""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def drafted(body: str) -> list[tuple[str, list[tuple[str, str | None, str | None]]]]:
    """A squash body as its messages, in order: (the message's text, line by line, its
    Signatures) - the first Signature the drafter, the rest co-drafters. A message is
    closed by its Signatures, so text after them opens the next; text with no Signature
    after it is the forge's own and is not a message."""
    out: list[tuple[str, list[tuple[str, str | None, str | None]]]] = []
    text: list[str] = []
    chain: list[tuple[str, str | None, str | None]] = []
    for line in body.splitlines():
        read = registry.read_signature(line)
        if read is not None:
            chain.append(read)
        elif line.strip():
            if chain:
                out.append(('\n'.join(text), chain))
                text, chain = [], []
            text.append(' '.join(line.split()))
    if chain:
        out.append(('\n'.join(text), chain))
    return out


def messages() -> list[tuple[str, str, list[tuple[str, str | None, str | None]]]]:
    """Every signed message on main: (the commit on main, the text, its Signatures)."""
    log = subprocess.run(['git', '-C', str(REPO), 'log', REF, '--format=%h%x1f%b%x1e'],
                         capture_output=True, text=True, check=True).stdout
    out = []
    for entry in log.split('\x1e'):
        if not entry.strip():
            continue
        commit, body = entry.strip('\n').split('\x1f', 1)
        out += [(commit, text.removeprefix('* '), chain) for text, chain in drafted(body)]
    return out


def held(provider: str, session: str) -> list[transport.Session]:
    """The copies the store holds of a session named by its first eight characters, in
    any room's directory, the fullest first - a session moves with its workspace and is
    carried between rooms, so one session has several copies and the longest holds the rest."""
    adapter = transport.adapter(provider)
    store = transport.store(provider)
    if adapter is None or not store.is_dir():
        return []
    copies = [s for room in sorted(p for p in store.iterdir() if p.is_dir())
              for s in adapter.held_sessions(room) if s.id.startswith(session)]
    return sorted(copies, key=lambda s: s.size, reverse=True)


def rooms_of(provider: str) -> list[str]:
    """The rooms whose sessions the provider's store holds."""
    store = transport.store(provider)
    return sorted(p.name for p in store.iterdir() if p.is_dir()) if store.is_dir() else []


def live(provider: str, session: str) -> transport.Session | None:
    """This room's live copy of the session, where its live store is mounted and holds it."""
    row = next((r for r in registry.providers() if r['provider'] == provider), None)
    adapter = transport.adapter(provider)
    mount = registry.mount(row) if row else None
    if adapter is None or mount is None or not mount.is_dir():
        return None
    return next((s for s in adapter.live_sessions(mount) if s.id.startswith(session)), None)


def survey() -> tuple[dict, list, int, str]:
    """The join's facts: per drafting session {(machine, provider, session): its messages
    as (commit, text)}, the messages a machine alone signed as (machine, commit, text),
    the count of co-drafting Signatures, and the commit main stands at."""
    sessions: dict[tuple[str, str, str], list[tuple[str, str]]] = {}
    alone: list[tuple[str, str, str]] = []
    co = 0
    for commit, text, chain in messages():
        machine, provider, session = chain[0]
        co += len(chain) - 1
        if provider is None or session is None:
            alone.append((machine, commit, text))
        else:
            sessions.setdefault((machine, provider, session), []).append((commit, text))
    head = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--short', REF],
                          capture_output=True, text=True).stdout.strip()
    return sessions, alone, co, head


def _capture(machine: str, provider: str, session: str) -> str:
    """The capture that brings the session's record level, and where it runs: only the
    room whose live store holds a session can capture it. A machine that is no room of
    the store - a session run in the provider's cloud, or under no binding - has no such
    store, so the session is resumed on a room first."""
    capture = f'corpus-yoga agent capture --provider {provider} --id {session}'
    if machine == bound_machine():
        return capture
    if machine in rooms_of(provider):
        return f'on {machine}, {capture}'
    return f'{machine} is no room of the store - resume the session on a room, then {capture}'


@dataclass
class Named:
    sessions_named: int
    held: int
    held_nowhere: dict[str, facts.Command | facts.Act] | None = None   # by session: the capture that would hold it, or what the reader does first


@dataclass
class Alone:
    """The messages signed by a machine alone: the room's own shell."""
    messages: int
    read_by: str = 'corpus-yoga agent list-drafters, each message against its drafter\'s record'


@dataclass
class Brief:
    """Per provider, the sessions main names as drafters and how many the store holds."""
    ref: str
    head: str
    providers: dict[str, Named]
    alone: Alone

    def facts(self) -> dict:
        return {**self.providers, 'a machine alone': self.alone}


def brief() -> Brief | None:
    """The bare noun's facts: per provider, the sessions main names as drafters and how
    many the store holds. Opens no session."""
    sessions, alone, _co, head = survey()
    if not sessions and not alone:
        return None
    out = Brief(REF, head, {}, Alone(len(alone)))
    for provider in sorted({p for _m, p, _s in sessions}):
        named = sorted(k for k in sessions if k[1] == provider)
        absent = [k for k in named if not held(k[1], k[2])]
        remedies = {'/'.join(k): _capture(*k) for k in absent}
        out.providers[provider] = Named(len(named), len(named) - len(absent), {
            session: facts.Command(remedy, 'captures it') if remedy.startswith('corpus-yoga ') else facts.Act(remedy)
            for session, remedy in remedies.items()} or None)
    return out


def report() -> int:
    """The verb: both properties, per provider and per session, each message a session is
    said to have drafted read against that session's held record. One verdict, the last line."""
    sessions, alone, co, head = survey()
    total = sum(len(v) for v in sessions.values()) + len(alone)
    print(f'drafters: {REF} @ {head} - {total} signed message(s); the first Signature of each names its drafter')
    unheld: list[str] = []
    unwritten = 0
    declared = registry.provider_names()
    for provider in sorted({p for _m, p, _s in sessions}):
        named = sorted(k for k in sessions if k[1] == provider)
        copies = {k: held(k[1], k[2]) for k in named}
        print(f'  {provider}: {len(named)} session(s) named, {sum(1 for k in named if copies[k])} held'
              + ('' if provider in declared else f' - {provider} is no row of rsc/provider/providers.csv'))
        adapter = transport.adapter(provider)
        for key in named:
            texts = sessions[key]
            name = '/'.join(key)
            if not copies[key] or adapter is None:
                unheld.append(name)
                print(f'    {name}: {len(texts)} message(s); held nowhere - the corpus is behind: {_capture(*key)}')
                continue
            fullest = copies[key][0]
            record = letters(' '.join(adapter.written(fullest)))
            short = [(c, t) for c, t in texts if not windows(t)]
            judged = [(c, t) for c, t in texts if windows(t)]
            missing = [(c, t) for c, t in judged if not any(w in record for w in windows(t))]
            unwritten += len(missing)
            line = f'    {name}: {len(texts)} message(s), {len(judged) - len(missing)} written by it'
            if short:
                line += f', {len(short)} too short to tell'
            if missing:
                line += f', {len(missing)} not in its held record ({fullest.size / 1e6:.1f}M)'
                now = live(key[1], key[2])
                if now is not None and now.size > fullest.size:
                    line += (f' - this room\'s live record holds {now.size / 1e6:.1f}M, so the held one is behind: '
                             f'{_capture(*key)}')
                elif key[0] != bound_machine() and key[0] in rooms_of(key[1]):
                    line += f' - the held record may be behind: {_capture(*key)}'
                else:
                    line += ' - the record does not carry them'
            print(line)
            for commit, text in missing:
                print(f'      {REF.split("/")[-1]} {commit}: {" ".join(text.split())[:96]}')
    rooms: dict[str, int] = {}
    for machine, _commit, _text in alone:
        rooms[machine] = rooms.get(machine, 0) + 1
    if alone:
        print(f'  a machine alone: {len(alone)} message(s) ('
              + ', '.join(f'{m} {n}' for m, n in sorted(rooms.items()))
              + ') - the room\'s own shell; nothing is claimed of the drafter')
    if co:
        print(f'  co-drafted: {co} later Signature(s), each a session or a room that amended or replayed a message another drafted')
    named_count = len(sessions)
    verdict = f'{named_count - len(unheld)} of {named_count} session(s) main names as drafters are held'
    if unheld:
        verdict += f' - the corpus is behind by {", ".join(unheld)}'
    verdict += (f'; {unwritten} message(s) are not in their drafter\'s held record' if unwritten
                else '; every message judged is in its drafter\'s record')
    print(f'drafters: {verdict}')
    return 0
