#!/usr/bin/env python
"""
page_declaration.py - what the corpus page declares of each conversation, and the lag between those
declarations and the corpus now (issues/1000). One derivation, three readers: the render
writes the declarations into the page, the page shows them on its bars, and bare
`corpus-yoga site` reads them back against data/output/markdown.

A conversation declares three metrics - its human turns, its assistant turns and the bytes
of its markdown. The page lags where any differs from the corpus now; where any has
decreased the lag is a regression, said as a warning, since a conversation does not
shrink: a format, serialisation or schema change is speaking. Reads; writes nothing.
"""
import json
import re
import sys
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path

SELF = 'src/main/page_declaration.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
from markdown_projection import corpus_index, turn_seq  # noqa: E402 - the format authority, reading back what it wrote

METRICS = ('human', 'assistant', 'bytes')
TABLE = re.compile(r'<script[^>]*id="data-chats"[^>]*>(.*?)</script>', re.S)
TURN = re.compile(r'^## (?:Human|Claude|Gemini) [^\n]*<a id="([^"]+)"(?: data-at="([^"]+)")?></a>', re.M)
UUID7 = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$')


def turn_instants(md: str) -> list[datetime]:
    """Each turn's instant, in order, where the markdown says it (issues/1007): the instant the
    projection wrote beside the anchor, else the creation instant a v7 uuid carries in its
    first 48 bits; a turn anchored by role and count alone, with no instant, says none."""
    out: list[datetime] = []
    for anchor, at in TURN.findall(md):
        if at:
            out.append(datetime.strptime(at, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc))
        elif UUID7.match(anchor):
            out.append(datetime.fromtimestamp(int(anchor.replace('-', '')[:12], 16) / 1000, tz=timezone.utc))
    return out


def declared_of(md: str) -> dict[str, int]:
    """A rendered conversation's declaration: its turns by role, from the role headings the
    projection wrote, and its bytes."""
    roles = [role for role, _body in turn_seq(md)]
    return {'human': roles.count('H'), 'assistant': roles.count('A'), 'bytes': len(md.encode())}


def corpus_declarations(md_root: Path) -> dict[str, dict[str, int]]:
    """Every projected conversation's declaration now, by its id."""
    out: dict[str, dict[str, int]] = {}
    for _ordinal, stem, _title, cid in corpus_index(md_root):
        provider, channel, fname = stem.split('/')
        out[cid] = declared_of((md_root / provider / channel / 'conversations' / f'{fname}.md').read_text())
    return out


def page_declarations(html: str) -> dict[str, dict[str, int]] | None:
    """What the page declares per conversation, by its id, from its data-chats block; None where
    the page declares no counts - one rendered before the declarations were written."""
    found = TABLE.search(html)
    if not found:
        return None
    table = json.loads(found.group(1))
    columns = table.get('columns', [])
    if not all(metric in columns and 'uuid' in columns for metric in METRICS):
        return None
    at = {name: columns.index(name) for name in ('uuid', *METRICS)}
    return {row[at['uuid']]: {metric: int(row[at[metric]]) for metric in METRICS} for row in table['rows']}


@dataclass
class Lag:
    """The page against the corpus: per conversation, each metric from the page's value to the
    corpus's where they differ; the conversations whose metrics decreased; those the corpus
    holds and the page lacks; those the page holds and the corpus has lost."""
    lagging: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)
    regressed: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)
    absent_from_page: list[str] = field(default_factory=list)
    gone_from_corpus: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.lagging or self.regressed or self.absent_from_page or self.gone_from_corpus)


def lag(page: dict[str, dict[str, int]], corpus: dict[str, dict[str, int]]) -> Lag:
    out = Lag()
    for cid, now in sorted(corpus.items()):
        was = page.get(cid)
        if was is None:
            out.absent_from_page.append(cid)
            continue
        moved = {metric: (was[metric], now[metric]) for metric in METRICS if was[metric] != now[metric]}
        if not moved:
            continue
        if any(new < old for old, new in moved.values()):
            out.regressed[cid] = moved
        else:
            out.lagging[cid] = moved
    out.gone_from_corpus = sorted(cid for cid in page if cid not in corpus)
    return out
