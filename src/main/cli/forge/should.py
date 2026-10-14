#!/usr/bin/env python
"""should.py - the one grammar of an issue as the forge raises it (#887): a title that is a
should, a body in .github/ISSUE_TEMPLATE.md's sections, and relations that are wired, never
narrated.

The forge writes the Signature, the as-at anchor and the supersession line; the drafter's
body carries `## currently` with `### as is`, and `## but, in future`. A phrase that claims
a relation - blocked by, blocks, part of, supersedes, closes, sub-issue - is refused in prose
outside backticks, since the raise's arguments wire what the phrase only narrated.
"""
import re
import sys
from pathlib import Path

SELF = 'src/main/cli/forge/should.py'
_file = Path(__file__).resolve()
assert [p for p in _file.parents if p / SELF == _file], f'{_file} is not at its declared address {SELF}'
sys.path.insert(0, str(_file.parent))
import aim  # noqa: E402 - bare(), the one stripping of mentions

SECTIONS = ('## currently', '### as is', '## but, in future')
WRITTEN = ('Signature:', '### as at')
_SHOULD = re.compile(r'\bshould\b')
_NARRATED = re.compile(r'\b(blocked by|blocks|part of|supersedes|closes) #\d+|\bsub-?issues?\b', re.I)


def check_title(title: str) -> None:
    """A title is one should: the word stands in it, and no `#` does."""
    if not _SHOULD.search(title):
        raise ValueError(f'the title is not a should - the word is absent: {title[:80]}')
    if '#' in title:
        raise ValueError(f'the title holds #, which a should never names: {title[:80]}')


def check_body(text: str) -> None:
    """The drafter's body: the template's sections in order, nothing the forge writes, and
    no relation narrated in prose."""
    at = -1
    for heading in SECTIONS:
        found = text.find(heading)
        if found < at:
            raise ValueError(f'the body lacks {heading}, or has it out of the template\'s order')
        at = found
    for own in WRITTEN:
        if own in text:
            raise ValueError(f'the body carries {own}, which the forge writes')
    narrated = _NARRATED.search(aim.bare(text))
    if narrated:
        raise ValueError(f'the body narrates a relation, {narrated.group(0)!r}; the raise\'s arguments wire it')


def as_at(sha: str, subject: str, machine: str, date: str) -> str:
    """The anchor, derived from the forge's main: its sha, the PR its subject names, the
    machine and the date of the raise."""
    merged = re.search(r'\(#(\d+)\)\s*$', subject)
    return f'main @ {sha[:7]}' + (f', after #{merged.group(1)} merged' if merged else '') + f'; raised from {machine} on {date}'


def compose(signature: str, text: str, anchor: str, supersedes: int | None) -> str:
    """The body as raised: the Signature, the as-at beneath `## currently`, the drafter's
    text, and the supersession line last where one is wired."""
    body = text.strip('\n').replace('## currently', f'## currently\n\n### as at\n\n{anchor}', 1)
    tail = f'\n\n- Supersedes #{supersedes}.' if supersedes else ''
    return f'{signature}\n\n{body}{tail}\n'
