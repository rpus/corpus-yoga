"""
stage.py - where a captured unit stands to the held one, per kind of data, and the
stage a capture writes to before promotion (#687).

A capture writes what its source returned under tmp/stage, at the address it will have
under data/input - tmp/stage/<provider>/<channel>/<capture>/... - and reads nothing (L10). Promotion is the one reduce over stage
against store: it relates each staged unit to the held unit of the same address, and
writes only where the relation licenses it - never where anything held would be lost
(L4), naming the rest (L6). One relation vocabulary, src/main/append_only.py's, serves
every kind; what differs per kind is the MEASURE the relation is taken over:

    session          the bytes of the log - an append-only stream, related by prefix
    api capture      the set of message uuids the conversation holds
    dom capture      (human turns, total turns) of the rendered markdown - the monotone
                     measure of a scrape (markdown_projection.turn_extent)
    export           a whole directory, either new or held: never merged
    anything else    the bytes

Each measure is a function of the unit's files alone, so a unit may be related
without the store being read by its capture.
"""
import json
import shutil
import sys
from pathlib import Path

SELF = 'src/main/stage.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
from append_only import Relation, relate  # noqa: E402
from markdown_projection import turn_extent  # noqa: E402

STAGE = REPO / 'tmp' / 'stage'
STORE = REPO / 'data' / 'input'


def staged(store_path: Path) -> Path:
    """The stage twin of a store path: the same address under tmp/stage."""
    return STAGE / store_path.relative_to(STORE)


def held(stage_path: Path) -> Path:
    """The store twin of a staged path."""
    return STORE / stage_path.relative_to(STAGE)


def kind(rel: Path) -> str:
    """The kind of unit at an address relative to data/input, by its channel and
    capture segments: <provider>/<channel>/<capture>/..."""
    parts = rel.parts
    if len(parts) >= 3:
        channel, capture = parts[1], parts[2]
        if channel == 'code':
            return 'session'
        if capture == 'API-capture':
            return 'api'
        if capture == 'DOM-capture':
            return 'dom'
        if capture == 'bulk-export':
            return 'export'
    return 'bytes'


def units(root: Path) -> list[Path]:
    """The promotable units under a root (the stage or the store), each a path relative
    to it: a session is its log file; an api capture and a
    dom capture are their conversation directory; an export is its data-* directory; a
    file at a unit's address (an ordering capture, a manifest) and anything else is a
    file of its own."""
    out = []
    for f in sorted(p for p in root.rglob('*') if p.is_file()):
        rel = f.relative_to(root)
        unit = Path(*rel.parts[:4]) if kind(rel) in ('api', 'dom', 'export') and len(rel.parts) > 4 else rel
        if unit not in out:
            out.append(unit)
    return out


def overlay(out: Path) -> tuple[int, int]:
    """A view of data/input with this room's stage laid over it, as a tree of links under
    out: every unit of the store linked at its address, then every staged unit linked
    over it. The pipelines read the view where they would read data/input, so a mint
    is tested over what the room has captured before the merge that licenses its
    promotion (#687). Returns (units of the store, units of the stage) linked."""
    if out.exists():
        shutil.rmtree(out)
    counts = []
    for root in (STORE, STAGE):
        n = 0
        if root.is_dir():
            for unit in units(root):
                link = out / unit
                if link.is_symlink() or link.exists():
                    link.unlink() if link.is_symlink() or link.is_file() else shutil.rmtree(link)
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(root / unit)
                n += 1
        counts.append(n)
    return counts[0], counts[1]


def _api_measure(unit_dir: Path) -> bytes | None:
    j = unit_dir / f'{unit_dir.name}.json'
    if not j.is_file():
        return None
    try:
        c = json.loads(j.read_text())
    except ValueError:
        return None
    ids = sorted(m['uuid'] for m in c.get('chat_messages', []) if m.get('uuid'))
    return ('\n'.join(ids) + '\n').encode()


def _dom_measure(unit_dir: Path) -> tuple[int, int] | None:
    mds = sorted(unit_dir.glob('*.md'))
    if not mds:
        return None
    return max(turn_extent(m.read_text()) for m in mds)


def _by_extent(incoming: tuple[int, int], existing: tuple[int, int] | None) -> Relation:
    """A scrape's (human turns, total turns) against the held one: an append-only
    conversation's extent only grows, so a scrape that holds no fewer on either count
    extends, one that holds fewer on either is the short walk (AHEAD - the held is
    ahead of it), and one that grew on one count and shrank on the other diverged."""
    if existing is None:
        return Relation.ABSENT
    if incoming == existing:
        return Relation.IDENTICAL
    if incoming[0] >= existing[0] and incoming[1] >= existing[1]:
        return Relation.EXTENDS
    if incoming[0] <= existing[0] and incoming[1] <= existing[1]:
        return Relation.AHEAD
    return Relation.DIVERGED


def relation(unit: Path) -> tuple[Relation, str]:
    """Where the staged unit stands to the held one, and the measure's own words."""
    k = kind(unit)
    s, h = STAGE / unit, STORE / unit
    if s.is_file() and k in ('api', 'dom', 'export'):
        k = 'bytes'                                   # a file at a unit's address, not a unit
    if k == 'export':
        if not h.exists():
            return Relation.ABSENT, 'a new export'
        return Relation.IDENTICAL if _tree_bytes(s) == _tree_bytes(h) else Relation.DIVERGED, \
            'an export is held whole or not at all'
    if k == 'api':
        incoming, existing = _api_measure(s), (_api_measure(h) if h.exists() else None)
        if incoming is None:
            return Relation.DIVERGED, 'the staged capture holds no readable conversation json'
        r = relate(incoming, existing)
        n_in, n_ex = incoming.count(b'\n'), (existing or b'').count(b'\n')
        return _by_set(s, h, r), f'{n_ex} -> {n_in} message(s)'
    if k == 'dom':
        incoming, existing = _dom_measure(s), (_dom_measure(h) if h.exists() else None)
        if incoming is None:
            return Relation.DIVERGED, 'the staged scrape holds no markdown'
        words = lambda m: f'{m[0]} human turns of {m[1]}'
        return _by_extent(incoming, existing), f'{words(existing) if existing else "nothing"} -> {words(incoming)}'
    incoming, existing = s.read_bytes(), (h.read_bytes() if h.exists() else None)
    r = relate(incoming, existing)
    return r, f'{len(existing or b"")} -> {len(incoming)} bytes'


def _by_set(s: Path, h: Path, prefix_relation: Relation) -> Relation:
    """An api capture's messages are a set, not a stream: EXTENDS means every held uuid
    is still present, AHEAD that the staged capture lost some, DIVERGED that each side
    has uuids the other lacks."""
    if prefix_relation in (Relation.ABSENT, Relation.IDENTICAL):
        return prefix_relation
    a = set((_api_measure(s) or b'').split()); b = set((_api_measure(h) or b'').split())
    if b <= a:
        return Relation.EXTENDS
    if a <= b:
        return Relation.AHEAD
    return Relation.DIVERGED


def _tree_bytes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}
