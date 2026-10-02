#!/usr/bin/env python
"""
vintage.py - a bulk export's name read by its vintage, the one export-ordering authority.

An export directory's name arrives from outside, and its grammars are data:
rsc/naming/export_dir_vintages.csv, one row per vintage, each a pattern with named groups
- epoch and hex8 where the vintage carries them, datetime where it carries that. Exports
order by the instant whose meaning the flow states (the maintainer's ruling, 2026-08-24):
the explicit datetime where the vintage has one, else the epoch. Every reader of an
export's name - the deposits, the frontier, the project pages, the store - reads it here.
"""
import csv
import re
from datetime import datetime, timezone
from pathlib import Path

SELF = 'src/main/pipeline/chat-export/vintage.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
VINTAGES_CSV = REPO / 'rsc' / 'naming' / 'export_dir_vintages.csv'


def vintages() -> list[tuple[str, re.Pattern]]:
    """The export-dir naming vintages, as data, file order first-match."""
    with VINTAGES_CSV.open() as f:
        return [(row['id'], re.compile(row['pattern'])) for row in csv.DictReader(f)]


def vintage_match(name: str) -> tuple[str | None, dict]:
    for vintage_id, pattern in vintages():
        m = pattern.match(name)
        if m:
            return vintage_id, m.groupdict()
    return None, {}


def export_time(name: str) -> datetime | None:
    """The export's ordering instant, per its name's vintage: the EXPLICIT datetime where
    the vintage carries one (v3: the manifest's created_at to the second; v1: the name's
    core), else the epoch (v2's only instant); None where no vintage reads the name."""
    _vintage_id, groups = vintage_match(name)
    if groups.get('datetime'):
        return datetime(*map(int, groups['datetime'].split('-')), tzinfo=timezone.utc)
    if groups.get('epoch'):
        return datetime.fromtimestamp(int(groups['epoch']), tz=timezone.utc)
    return None


def short(name: str) -> str:
    """The export's own 8-hex capture token, for compact citation - the whole name where
    its vintage carries none (v1)."""
    _vintage_id, groups = vintage_match(name)
    return groups.get('hex8') or name
