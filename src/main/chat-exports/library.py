#!/usr/bin/env python
"""
library.py — uuid-keyed resolution of the durable artifact library.

data/output/artifacts/downloaded/ outlives any one export batch, so its directories are
keyed by identity with presentation as dressing: <ordinal>-<slug>-<uuid8>, where
<uuid8> (the first 8 hex digits of the conversation uuid) is the resolution key
and <ordinal>-<slug> is the batch's canonical presentation name — carried for
humans (listings read and sort in conversation order) but never trusted by
machines: ordinals renumber whenever the corpus changes, so dir_for() REFRESHES
the dressing to the current numbering every time a consumer touches the dir.
A dir whose conversation is absent from the current corpus (deleted live) keeps
whatever dressing it last had — or none — the absence of a current number being
itself a signal. Ordinals and slugs contain no hyphens (slug() maps
non-alphanumerics to '_'), so the final hyphen always delimits the uuid8.

Resolution is always by uuid8 suffix (glob "*-<uuid8>"), never by dressing: a
conversation renamed or renumbered simply gets fresh dressing on next touch.

The naming vintages this recognises are recorded as data:
rsc/naming/library_dir_vintages.csv.
"""
import sys
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[3] / 'data' / 'output' / 'artifacts' / 'downloaded'


def assert_uuid8_unique(uuids) -> None:
    """The census the dressing scheme rests on: uuid8 (32 bits) is an identity
    key only while no two conversations share a prefix — a property to VERIFY
    against the population, never to purchase from probability (user law,
    2026-07-08; the check is O(n), the failure it prevents is two
    conversations' artifacts silently interleaved in one dir). Exits loudly,
    naming the full colliding uuids — a collision means the scheme needs
    longer prefixes, not a shrug."""
    by_u8: dict[str, set[str]] = {}
    for u in uuids:
        by_u8.setdefault(u[:8], set()).add(u)
    clashes = {u8: us for u8, us in by_u8.items() if len(us) > 1}
    if clashes:
        lines = [f'  {u8}: ' + ', '.join(sorted(us)) for u8, us in sorted(clashes.items())]
        sys.exit('error: uuid8 prefix collision — the library dressing scheme cannot '
                 'key these conversations:\n' + '\n'.join(lines))


def find(uuid: str, root: Path = LIBRARY) -> Path | None:
    """The existing library dir for this conversation, or None. Recognises the
    canonical suffix form AND the short-lived 2026-07-05 uuid8-PREFIX vintage
    ("<uuid8>-<slug>"), so a library pulled at that vintage heals on first touch
    (dir_for renames whatever find returns) instead of silently duplicating —
    the exact bug uuid-keying exists to prevent. (No false positives either way:
    an ordinal prefix is 2-3 digits, never 8 hex + '-'; a slug tail would have
    to equal this conversation's uuid8 exactly.)"""
    if not root.is_dir():
        return None
    hits = sorted(root.glob(f'*-{uuid[:8]}')) or sorted(root.glob(f'{uuid[:8]}-*'))
    return hits[0] if hits else None


def dir_for(uuid: str, dressing: str, root: Path = LIBRARY) -> Path:
    """The library dir for this conversation, renamed to carry the CURRENT
    presentation dressing (the batch's "<ordinal>-<slug>" name) if it exists
    under stale dressing; else the path a new one should be created at."""
    canonical = root / f'{dressing}-{uuid[:8]}'
    existing = find(uuid, root)
    if existing is None:
        return canonical
    if existing != canonical:
        existing.rename(canonical)  # dressing refresh — identity (the suffix) unchanged
    return canonical
