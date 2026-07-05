#!/usr/bin/env python
"""
library.py — uuid-keyed resolution of the durable artifact library.

lib/artifacts/downloaded/ outlives any one export batch, so its directories are
keyed by identity, not by presentation: <uuid8>-<slug>, where <uuid8> is the
first 8 hex digits of the conversation uuid and <slug> is display dressing.
Ordinals renumber whenever the corpus changes (a conversation deleted live, an
empty stub quarantined) — an ordinal-keyed durable store silently duplicates or
mis-attributes after every renumbering (bitten twice). The rule: the LLM speaks
ordinals, storage speaks uuid, presentation re-derives ordinals.

Resolution is always by uuid prefix (glob "<uuid8>-*"), never by slug: a
conversation renamed live gets a fresh slug in new batches, but its library
directory — found by uuid — simply keeps its old dressing.
"""
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[3] / 'lib' / 'artifacts' / 'downloaded'


def find(uuid: str, root: Path = LIBRARY) -> Path | None:
    """The existing library dir for this conversation, or None."""
    hits = sorted(root.glob(f'{uuid[:8]}-*')) if root.is_dir() else []
    return hits[0] if hits else None


def dir_for(uuid: str, slug: str, root: Path = LIBRARY) -> Path:
    """The library dir for this conversation: the existing one (whatever its slug
    dressing), else the path a new one should be created at."""
    return find(uuid, root) or root / f'{uuid[:8]}-{slug}'
