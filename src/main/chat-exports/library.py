#!/usr/bin/env python
"""
library.py — uuid-keyed resolution of the durable artifact library.

lib/artifacts/downloaded/ outlives any one export batch, so its directories are
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
"""
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[3] / 'lib' / 'artifacts' / 'downloaded'


def find(uuid: str, root: Path = LIBRARY) -> Path | None:
    """The existing library dir for this conversation, or None."""
    hits = sorted(root.glob(f'*-{uuid[:8]}')) if root.is_dir() else []
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
