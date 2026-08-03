"""
Where one append-only stream stands to another.

A stream that only ever grows carries its whole history as a byte prefix, so two
copies of one stream are related by prefix alone. Five relations exhaust the
possibilities, and each names what the holder of the destination may do:

    ABSENT     nothing to compare — the incoming stream is the first copy
    IDENTICAL  the two hold the same bytes
    EXTENDS    the destination is a strict prefix of the incoming — a fast-forward
    AHEAD      the incoming is a strict prefix of the destination — a stale copy
    DIVERGED   neither is a prefix of the other — two writers, or one rewritten

The relation is direction-blind: it says how the streams stand, never which side
should win, and never how to say so.
"""
from enum import Enum


class Relation(Enum):
    ABSENT = 'absent'
    IDENTICAL = 'identical'
    EXTENDS = 'extends'
    AHEAD = 'ahead'
    DIVERGED = 'diverged'


def relate(incoming: bytes, destination: bytes | None) -> Relation:
    if destination is None:
        return Relation.ABSENT
    if incoming == destination:
        return Relation.IDENTICAL
    if incoming.startswith(destination):
        return Relation.EXTENDS
    if destination.startswith(incoming):
        return Relation.AHEAD
    return Relation.DIVERGED


def may_replace(relation: Relation) -> bool:
    return relation in (Relation.ABSENT, Relation.EXTENDS)


def growth(incoming: bytes, destination: bytes | None) -> tuple[int, int]:
    return len(destination or b''), len(incoming)
