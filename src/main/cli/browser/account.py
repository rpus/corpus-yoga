#!/usr/bin/env python
"""
account.py - each provider's account as last fetched (corpus-yoga browser fetch records it at
tmp/browser/fetch/<provider>.json) against the captures: which chats are new or have grown since
their capture, each with the capture that brings it level. Read by bare `corpus-yoga browser`;
reads, never sends.

  claude - the account's list gives each chat's updated_at, compared against each captured
  JSON's: new (never captured) and grown (updated since capture).
  gemini - the list gives the chats; the end of each captured chat's last exchange, as it
  rendered, is compared against the capture's last turns, alphanumeric-normalized so
  markdown-vs-rendered differences wash out. A chat holds what it held, so a changed end is a
  grown chat (rendering edge cases err toward recapture, e.g. a response ending in maths).
"""
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SELF = 'src/main/cli/browser/account.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
import tier  # noqa: E402 - the tiers, one home (issues/702)
import facts  # noqa: E402
import spell  # noqa: E402
from markdown_projection import turn_seq  # noqa: E402 - the format authority owns the parsers

RECORD = tier.TMP / 'browser' / 'fetch'   # <provider>.json, the account as last fetched


@dataclass
class Moved:
    """A chat new or grown since its capture, with the capture that acts on it."""
    standing: str
    remedy: facts.Command | facts.Would


@dataclass
class Account:
    """One provider's account as last fetched, against the captures."""
    fetched: str
    chats_listed: int
    new_since_capture: int
    grown_since_capture: int
    captured_but_no_longer_listed: int
    ends_compared: int | None = None
    chats: dict[str, Moved] | str = facts.named('chats', default='none')   # by chat


@dataclass
class Unfetched:
    """An account no fetch has recorded, with the fetch that records it."""
    standing: str
    remedy: facts.Would


def alnum(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())


CAPTURES = {'claude': ('claude', 'chat', 'API-capture'), 'gemini': ('gemini', 'chat', 'DOM-capture')}


def captured(provider: str, root: Path | None = None) -> dict[str, Path]:
    """Each captured chat of the provider, by its id, under the input root."""
    where = (root or tier.DATA / 'input').joinpath(*CAPTURES[provider])
    return {d.name: d for d in sorted(where.iterdir()) if d.is_dir()} if where.is_dir() else {}


def moved(provider: str, findings: list[tuple[str, str, str]]) -> dict[str, Moved] | str:
    """Each chat new or grown since its capture, with the command that acts on it - never a
    bare id in a list that has left its provider behind."""
    return {cid: Moved(facts.phrase('{kind} - {detail}', kind=kind, detail=detail), facts.Would(spell.line('browser', 'capture', provider=provider, id=cid), {cid: 1}))
            for kind, cid, detail in findings} or 'none'


def account(provider: str, record: Path, root: Path | None = None) -> Account | Unfetched:
    """The provider's account as last fetched, against its captures; read, never sent."""
    if not record.is_file():
        return Unfetched(facts.phrase('unfetched - no fetch has recorded what the account holds'),
                         facts.Would(spell.line('browser', 'fetch', provider=provider), {f'{provider} account': 1}))
    held = json.loads(record.read_text())
    chats = captured(provider, root)
    found = []
    ends = None
    if provider == 'claude':
        updated = held['updated']
        listed = sorted(updated)
        for cid in listed:
            json_file = chats[cid] / f'{cid}.json' if cid in chats else None
            was = json.loads(json_file.read_text()).get('updated_at', '') if json_file and json_file.is_file() else None
            if cid not in chats:
                found.append(('new', cid, facts.phrase('never captured')))
            elif was is not None and updated[cid] > was:
                found.append(('grown', cid, facts.phrase('captured {captured} < updated {updated}', captured=was, updated=updated[cid])))
    else:
        listed = held['listed']
        found = [('new', cid, facts.phrase('never captured')) for cid in listed if cid not in chats]
        ends = 0
        for cid, end in sorted(held['ends'].items()):
            mds = sorted(chats[cid].glob('*.md')) if cid in chats else []
            if not mds:
                continue
            seq = turn_seq(mds[0].read_text())
            # Two probes, either match = current. The HUMAN probe is the robust one (typed
            # text renders literally); the agent probe can false-mismatch when a response
            # ends in rendered maths/markup, whose glyphs alnum-normalize away.
            probes = [alnum([b for r, b in seq if r == role][-1])[-120:] for role in ('H', 'A') if any(r == role for r, _ in seq)]
            probes = [p for p in probes if p]
            if not probes:
                continue
            ends += 1
            if not any(p in end for p in probes):
                found.append(('grown', cid, facts.phrase('"{name}" - rendered tail no longer matches the captured last turns', name=mds[0].stem)))
    return Account(held['fetched'], len(listed), sum(1 for k, _, _ in found if k == 'new'), sum(1 for k, _, _ in found if k == 'grown'),
                   len(set(chats) - set(listed)), ends, moved(provider, found))
