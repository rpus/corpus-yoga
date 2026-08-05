#!/usr/bin/env python
"""
accumulate.py — the CALCULUS `accumulate` operation, once.

    deposit a state under its stamp iff it differs from the nearest earlier
    deposit; deposits are immutable and outlive their producers; a same-stamp
    content mismatch is a CONFLICT.

Two stores accumulate: the chat-memory library (memories.py) and the
per-conversation summary store (summaries.py). Before this module they
each carried their own copy of the rule; the drift between them cost 196 redundant
summary deposits (issue #22). One implementation removes the class of bug —
including the writer/detector split, since the summary twin-detector evaluates the
SAME nearest_earlier_deposit the writer does, so it can never under-report what the
writer would refuse.

Why nearest-earlier, and not a folder-wide content set: these stores record a
TRAJECTORY, not a set. An unchanged reading deposits nothing, and each deposit is
named by the snapshot that FIRST exhibited it — so the store is the sequence of
changes, not the values ever produced. Given that:

  - a repeat with NOTHING between it and its twin is not an event: the reading
    never changed, and a fresh stamp would assert a change that did not happen
    (identical by construction) — suppress;
  - a repeat AFTER an intervening different reading IS an event: the oracle went
    to B and returned to A (identical by coincidence) — deposit, because a
    trajectory that omits the return is a false trajectory.

Nearest-earlier states exactly that distinction, so position is not a proxy here —
it is the semantics. A folder-wide set would erase every return.

The callers differ only in parameters — memories keys `.json` deposits with no
non-deposit siblings; summaries keys `.md` deposits beside index.md and a rolling
browser-capture.md, which `exclude` holds out of the comparison.
"""
from pathlib import Path


def deposits_in(store: Path, *, suffix: str, exclude=()):
    """The store's deposit files, name-sorted (== stamp-sorted, suffix constant).
    `exclude` names siblings that share the suffix but are not deposits
    (summaries' index.md, browser-capture.md)."""
    return sorted(p for p in store.glob(f'*{suffix}') if p.name not in exclude)


def nearest_earlier_deposit(store: Path, stamp: str, *, suffix: str, exclude=()):
    """The deposit with the greatest stamp STRICTLY before `stamp`, or None.
    Strict '<' so a deposit is never its own nearest-earlier — the writer (skips a
    reading identical to it) and the twin-detector (flags a deposit identical to
    it) must read this the same way, or the detector under-reports."""
    earlier = [p for p in deposits_in(store, suffix=suffix, exclude=exclude)
               if p.stem < stamp]
    return earlier[-1] if earlier else None


def accumulate(store: Path, stamp: str, content: str, *, suffix: str, exclude=()) -> str:
    """Deposit `content` under `stamp` iff it differs from the nearest earlier
    deposit. Returns one of:

      'deposited' — a new deposit was written;
      'unchanged' — nothing written: either the same stamp already holds this
                    content (idempotent re-run), or the nearest earlier deposit
                    is identical (the reading has not changed);
      'conflict'  — the same stamp already holds DIFFERENT content; nothing is
                    written and the existing deposit is left untouched (deposits
                    are immutable). The caller reports and fails the run.

    Reporting stays with the caller — each store speaks its own vocabulary."""
    dest = store / f'{stamp}{suffix}'
    if dest.exists():
        return 'unchanged' if dest.read_text() == content else 'conflict'
    prior = nearest_earlier_deposit(store, stamp, suffix=suffix, exclude=exclude)
    if prior is not None and prior.read_text() == content:
        return 'unchanged'
    dest.write_text(content)
    return 'deposited'
