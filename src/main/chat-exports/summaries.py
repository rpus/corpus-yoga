#!/usr/bin/env python
"""
summaries.py — deposit every distinct conversation summary durably.

The summary is a per-snapshot oracle READING of a conversation (a nondeterministic
emission: the same transcript has been observed to re-read differently — №99,
two exports ten hours apart, identical updated_at), carried by every bulk export
and every browser capture, and lossy between snapshots: the backend regenerates it
at will, exports supersede each other, captures refresh in place. Each distinct
reading is deposited once, durably, so batches and captures may churn while no
reading is ever lost — and supersede' summaries component recognises the
deposits as its unconditional licence.

The summary store and the chat-memory library are the two callers of the shared
CALCULUS accumulate operation (accumulate.py); this one keys deposits per
conversation, the library keys them per snapshot.

Layout (data/output/markdown/claude/chat/summaries/):
  <conversation-stem>/          # stem matches data/output/markdown/claude/chat/conversations/<stem>.md;
                                # renamed when ordinals renumber (the index's uuid is the key)
    index.md                    # the map: uuid, conversation link, one line per reading
    <export-ts>.md              # a distinct reading, verbatim, named by the FIRST export
                                # exhibiting it (ts format matches data/output/memories deposits)
    browser-capture.md          # the capture's reading, only while it matches no export
                                # deposit (rolling: recaptures refresh it; the export
                                # deposits are the immutable record)

Readings are deposited by the shared CALCULUS accumulate rule (accumulate.py):
content-deduplicated against the nearest earlier deposit, so a re-stamped unchanged
reading costs nothing while a genuine return still records. An <export-ts>.md, once
written, is never modified. Everything derives from the local corpora — L1:
re-running is silence on disk.

Usage (bare = status, the verb writes — the memories shape):
  src/run_python_script.sh src/main/chat-exports/summaries.py [sync] \\
      [--chat-exports-cache tmp/cache/chat-exports] [--browser-api data/input/claude/chat/browser-API] \\
      [--conversations-output data/output/markdown/claude/chat/conversations] \\
      [--summaries-output data/output/markdown/claude/chat/summaries]
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # src/ — modules both tiers import
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import REPO, find_api_json

from argparse_help import enrich, inherit_flags  # noqa: E402
from supersede import batch_time  # noqa: E402 — the one batch-ordering authority
from accumulate import accumulate, nearest_earlier_deposit  # noqa: E402 — the one deposit rule

# A summary folder holds <stamp>.md deposits beside two non-deposits: index.md
# (the map) and browser-capture.md (rolling). Both are held out of the accumulate
# comparison and the twin scan.
SUFFIX = '.md'
NON_DEPOSITS = {'index.md', 'browser-capture.md'}


def _ts(batch_name):
    """The batch's snapshot time in the data/output/memories deposit style (compact UTC)."""
    t = batch_time(batch_name)
    return t.strftime('%Y-%m-%dT%H%M%SZ') if t else None


def stems_by_uuid(conversations_output: Path):
    """{uuid: (stem, title)} from the projected conversation files' frontmatter —
    the current presentation names, so summary folders ride the same renumbering."""
    out = {}
    for f in sorted(conversations_output.glob('*.md')) if conversations_output.is_dir() else []:
        head = f.read_text()[:600]
        u = re.search(r'^uuid: ([0-9a-f-]{36})$', head, flags=re.M)
        t = re.search(r'^# (.+)$', head, flags=re.M)
        if u:
            out[u.group(1)] = (f.stem, t.group(1) if t else f.stem)
    return out


def readings_by_uuid(gen_root: Path):
    """{uuid: [(ts, summary), …]} across all atomised batches in snapshot order,
    collapsing each run of consecutive-identical readings to its first — each
    surviving pair is one distinct reading, stamped with the FIRST batch exhibiting
    it. (This pre-filters the reading STREAM; the durable deposit rule is the shared
    accumulate, applied per folder in sync.)"""
    floor = datetime.min.replace(tzinfo=timezone.utc)
    batches = sorted((d for d in gen_root.glob('data-*') if (d / 'json').is_dir()),
                     key=lambda d: batch_time(d.name) or floor)
    out = {}
    for b in batches:
        ts = _ts(b.name)
        if ts is None:
            continue
        for f in sorted((b / 'json').glob('*.json')):
            c = json.loads(f.read_text())
            u, s = c.get('uuid'), c.get('summary')
            if u and s:
                seq = out.setdefault(u, [])
                if not seq or seq[-1][1] != s:
                    seq.append((ts, s))
    return out


def capture_summaries(captures_dir: Path):
    """{uuid: summary} from the live-capture corpus (empty summaries dropped)."""
    out = {}
    for d in sorted(p for p in captures_dir.iterdir() if p.is_dir()) if captures_dir.is_dir() else []:
        api = find_api_json(d)
        if api is not None and api.get('summary'):
            out[api['uuid']] = api['summary']
    return out


def _write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text() == text:
        return False
    path.write_text(text)
    return True


def index_text(uuid, stem, title, deposit_names):
    """The folder's deterministic map — frontmatter carries the uuid (the rename
    key); the body links back to the conversation and lists every reading, all as
    named hyperlinks (clickable in any markdown renderer)."""
    lines = ['---', f'uuid: {uuid}', '---', '',
             f'# Summaries — {title}', '',
             f'Distinct readings of [the conversation](../../conversations/{stem}.md), '
             'each named by the snapshot that first exhibited it:', '']
    for n in deposit_names:
        label = ('browser capture (rolling)' if n == 'browser-capture.md'
                 else n[:-3] if n.endswith('.md') else n)
        lines.append(f'- [{label}]({n})')
    return '\n'.join(lines) + '\n'


def twins_of(folder: Path) -> list[Path]:
    """The folder's twin deposits: each byte-identical to its nearest earlier
    sibling — exactly what the shared accumulate rule would never write, so any
    such deposit is a defect in whatever wrote it. A genuine A→B→A recurrence is
    NOT a twin: its second A's nearest-earlier is B. Callers: status and sync's
    WARN."""
    deps = sorted(p for p in folder.glob('*.md') if p.name not in NON_DEPOSITS)
    out = []
    for p in deps:
        prior = nearest_earlier_deposit(folder, p.stem, suffix=SUFFIX, exclude=NON_DEPOSITS)
        if prior is not None and p.read_bytes() == prior.read_bytes():
            out.append(p)
    return out


def _warn_twins(root: Path) -> int:
    """Report the store's twin count — the standing detector, kept permanently
    now that the one-shot repair has retired. nearest_earlier_deposit cannot
    write a twin, so a nonzero count is a NEW defect to investigate, not the
    artifact class the repair cleared. WARN-prefixed so the run tail's atom
    hoisting carries it into every yoga pipeline run summary."""
    twins = sum(len(twins_of(d)) for d in root.iterdir() if d.is_dir()) \
        if root.is_dir() else 0
    if twins:
        print(f'WARN: {twins} twin deposit(s) in the summaries store — byte-identical '
              'to their nearest earlier sibling, which the deposit rule never writes:')
        print('    → investigate: this is a NEW defect in whatever wrote them. The '
              're-stamp bug is fixed and its one-shot repair retired; nothing in the '
              'current machinery can mint a twin.')
    return twins


def status(root: Path) -> int:
    """The bare-noun default: show the store's current state, write nothing.
    Deliberately store-only (pure directory listing): computing what a sync
    WOULD deposit means parsing every batch and capture — that is sync's job,
    and its dedup makes running it the cheaper way to find out."""
    folders = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    readings = rolling = 0
    for d in folders:
        for f in d.glob('*.md'):
            if f.name == 'index.md':
                continue
            rolling += (f.name == 'browser-capture.md')
            readings += (f.name != 'browser-capture.md')
    shown = root.relative_to(REPO) if root.is_relative_to(REPO) else root
    print(f'summaries: {len(folders)} conversation folder(s), {readings} deposited '
          f'reading(s), {rolling} rolling capture reading(s) in {shown}')
    _warn_twins(root)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description='The durable per-conversation summary store (memories semantics: '
                    'immutable, content-deduplicated). Bare shows status; `sync` writes.')
    sub = ap.add_subparsers(dest='verb')
    sync_p = sub.add_parser('sync')
    ap.add_argument('--chat-exports-cache', metavar='DIR',
                    default=str(REPO / 'tmp' / 'cache' / 'chat-exports'))
    ap.add_argument('--browser-api', metavar='DIR',
                    default=str(REPO / 'data' / 'input' / 'claude' / 'chat' / 'browser-API'))
    ap.add_argument('--conversations-output', metavar='DIR',
                    default=str(REPO / 'data' / 'output' / 'markdown' / 'claude' / 'chat' / 'conversations'))
    ap.add_argument('--summaries-output', metavar='DIR',
                    default=str(REPO / 'data' / 'output' / 'markdown' / 'claude' / 'chat' / 'summaries'))
    inherit_flags(ap, sync_p)
    enrich(ap, 'summaries')
    args = ap.parse_args()

    root = Path(args.summaries_output)
    if args.verb != 'sync':
        return status(root)
    stems = stems_by_uuid(Path(args.conversations_output))
    if not stems:
        # L8: absence is a signal. No projected corpus means an upstream failure
        # (or a corpus-less clone) — depositing under fallback names would file
        # readings wrongly and then hold them immutable. Skip, loudly.
        print(f'summaries: no projected conversations under {args.conversations_output} — '
              'skipping (deposits key on the projection; run the browser-captures pipeline first)')
        return 0
    readings = readings_by_uuid(Path(args.chat_exports_cache))
    captured = capture_summaries(Path(args.browser_api))

    # existing folders by their index's uuid — the rename key across renumberings
    existing = {}
    if root.is_dir():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            idx = d / 'index.md'
            if idx.exists():
                m = re.search(r'^uuid: ([0-9a-f-]{36})$', idx.read_text()[:300], flags=re.M)
                if m:
                    existing[m.group(1)] = d

    deposited = unchanged = renamed = conflicts = 0
    for u in sorted(set(readings) | set(captured)):
        stem, title = stems.get(u, (None, None))
        if stem is None:
            # never captured: name by the newest batch's piece OWNING it — exact
            # uuid match, never substring (a conversation's text can cite other
            # conversations' uuids; first-substring-wins once mis-filed ~55
            # readings into one folder, found 2026-07-13 when an upstream
            # failure emptied the stems map)
            stem = title = next((f.stem for b in sorted(Path(args.chat_exports_cache).glob('data-*'),
                                                        key=lambda d: d.name, reverse=True)
                                 for f in (b / 'json').glob('*.json')
                                 if json.loads(f.read_text()).get('uuid') == u), u[:8])
        folder = root / stem
        prior = existing.get(u)
        if prior is not None and prior != folder:
            prior.rename(folder)   # presentation renumbered; the deposit follows its conversation
            renamed += 1
        folder.mkdir(parents=True, exist_ok=True)

        texts = []
        # Each reading is stamped by the FIRST SURVIVING batch exhibiting it, so
        # disposing a batch re-stamps its readings under the next survivor. The
        # shared accumulate rule (nearest-earlier) suppresses the re-stamp — the
        # store remembers what the batch sequence forgets at disposal — while a
        # genuine A→B→A return still deposits, because A's nearest-earlier is then
        # B, not A. Without it the re-stamped reading deposited again, byte-
        # identical under a new key: 196 such twins accreted before the fix
        # (found 2026-07-23, reading-room's rehearsal; issue #22).
        for ts, s in readings.get(u, []):
            result = accumulate(folder, ts, s, suffix=SUFFIX, exclude=NON_DEPOSITS)
            if result == 'deposited':
                deposited += 1          # verbatim — the deposit IS the reading
            elif result == 'conflict':
                # the calculus accumulate contract (issue #22): a same-stamp
                # content mismatch is a CONFLICT, exit 1 — not a stderr aside
                print(f'  ✗ CONFLICT {stem}/{ts}.md: existing deposit differs from this '
                      'derivation — left untouched (deposits are immutable); investigate')
                conflicts += 1
            else:
                unchanged += 1
            texts.append(s)

        cap = captured.get(u)
        bc = folder / 'browser-capture.md'
        if cap and cap not in texts:
            if _write_if_changed(bc, cap):
                deposited += 1
        elif bc.exists():
            bc.unlink()                  # no longer unique: the export deposits carry it

        names = sorted(f.name for f in folder.glob('*.md') if f.name != 'index.md')
        _write_if_changed(folder / 'index.md', index_text(u, stem, title, names))

    print(f'summaries: {deposited} reading(s) deposited, {unchanged} already held, '
          f'{renamed} folder(s) renamed -> {root.relative_to(REPO) if root.is_relative_to(REPO) else root}'
          + (f'; {conflicts} CONFLICT(S)' if conflicts else ''))
    # the standing twin detector runs on every sync too — ambient in the run
    # tail via WARN-atom hoisting, not only on an explicit status invocation
    _warn_twins(root)
    return 1 if conflicts else 0


if __name__ == '__main__':
    # sys.exit, not a bare call: main()'s return IS the exit code, so a
    # CONFLICT can actually fail the run step (issue #22 — the bare call made
    # `yoga summaries sync` a step that could never exit non-zero, against L8)
    sys.exit(main())
