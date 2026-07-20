#!/usr/bin/env python
"""
accumulate_memories.py — accumulate every distinct chat-memory state into the
durable library, and project the accumulated timeline to markdown.

Bulk exports are the ONLY log of chat memories, and the memory document is a
mutable rolling summary — rewritten, and lossy, between exports. Conversations
accumulate by uuid (identity stable, ordinals drift); memory snapshots are
versions of ONE document, so here snapshot time IS the identity — the dual
keying (cf. library.py):

    output/memories/<batch snapshot time, ISO-8601 UTC>.json   (verbatim memories.json)

Per pipeline run, every batch's archived memory state (cache/<batch>/memories/,
written by archive_components.py) is deposited under its batch timestamp unless
the nearest earlier deposit already carries identical content — so an unchanged
memory costs nothing, a rewrite is preserved forever, and a reverted-then-back
document redeposits honestly. Deposits are never modified or removed; they
outlive their batches, which is the point: once a batch's memory state is
deposited, the batch's memories-divergence no longer blocks its deletion
(compare_batches stays unprejudiced — the deposit report here is the licence,
not a carve-out there).

The projection renders every deposit to output/markdown/claude/chat/memories/<stamp>.md (this
stage owns that subtree). The memory content is already markdown inside the
JSON string, so this is an unwrap, not a transformation — the served corpus
gains a diffable timeline of what claude.ai believed about the user at each
export.

Usage (wired into RUNME.sh after the per-batch stages):
    src/run_python_script.sh src/main/chat-exports/accumulate_memories.py \
      [--chat-exports-cache cache/chat-exports] [--memories-output output/memories] \
      [--markdown output/markdown/claude/chat/memories]
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from compare_batches import batch_time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import reconcile_dir  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
CHAT_EXPORTS_CACHE_DIR = REPO / 'cache' / 'chat-exports'
MEMORIES_OUTPUT_DIR = REPO / 'output' / 'memories'
MARKDOWN_DIR = REPO / 'output' / 'markdown' / 'claude' / 'chat' / 'memories'


def stamp_vintages() -> list[dict]:
    """Deposit-filename formats AS DATA: rsc/naming/memory_deposit_vintages.csv
    (id, status, pattern, strptime, note). The 'current' row's strptime is the
    one authority for writing stamps; legacy rows are recognised and normalised."""
    with open(REPO / 'rsc' / 'naming' / 'memory_deposit_vintages.csv') as f:
        return list(csv.DictReader(f))


def current_stamp_fmt() -> str:
    return next(v['strptime'] for v in stamp_vintages() if v['status'] == 'current')


def normalise_stamps(lib_dir: Path) -> int:
    """Heal legacy-vintage deposit filenames to the current format (no migrations,
    only normalisations — running this on a current store is silence). The
    snapshot time IS the identity, preserved exactly under reformatting; a rename
    collision with identical content drops the duplicate file, a differing one is
    a loud CONFLICT left in place."""
    vintages = stamp_vintages()
    fmt = current_stamp_fmt()
    conflicts = 0
    for f in sorted(lib_dir.glob('*.json')) if lib_dir.is_dir() else []:
        v = next((v for v in vintages if re.match(v['pattern'], f.stem)), None)
        if v is None or v['status'] == 'current':
            continue
        t = datetime.strptime(f.stem, v['strptime']).replace(tzinfo=timezone.utc)
        dest = f.with_name(t.strftime(fmt) + '.json')
        if dest.exists():
            if dest.read_text() == f.read_text():
                f.unlink()
                print(f'  {f.name}: duplicate of {dest.name} — dropped')
            else:
                conflicts += 1
                print(f'  ✗ CONFLICT: {f.name} and {dest.name} differ — both left in place')
        else:
            f.rename(dest)
            print(f'  {f.name} ({v["id"]}) -> {dest.name}')
    return conflicts


def memory_states(gen_root):
    """[(stamp, batch name, verbatim text)] for every batch with an archived memory,
    in snapshot-time order."""
    fmt = current_stamp_fmt()
    states = []
    for d in sorted(gen_root.glob('data-*')):
        f = d / 'memories' / 'memories.json'
        t = batch_time(d.name)
        if not f.exists() or t is None:
            continue
        stamp = t.astimezone(timezone.utc).strftime(fmt)
        states.append((stamp, d.name, f.read_text()))
    return sorted(states)


def deposit(states, lib_dir):
    """Deposit each state under its stamp unless the nearest earlier deposit is
    identical. Existing deposits are immutable; a same-stamp content mismatch is
    reported loudly and left alone."""
    lib_dir.mkdir(parents=True, exist_ok=True)
    conflicts = normalise_stamps(lib_dir)
    for stamp, batch, text in states:
        dest = lib_dir / f'{stamp}.json'
        if dest.exists():
            if dest.read_text() == text:
                status = '✓ deposited'
            else:
                status = '✗ CONFLICT: deposit exists with different content — investigate'
                conflicts += 1
        else:
            earlier = sorted(p for p in lib_dir.glob('*.json') if p.stem <= stamp)
            if earlier and earlier[-1].read_text() == text:
                status = f'unchanged since {earlier[-1].stem} — no deposit'
            else:
                dest.write_text(text)
                status = '✓ deposited (new)'
        print(f'  {batch}: memory state {stamp} {status}')
    deposits = sorted(lib_dir.glob('*.json'))
    print(f'output/memories: {len(deposits)} deposit(s)')
    return deposits, conflicts


def render(deposits, out_dir):
    """Unwrap each deposit's markdown to <stamp>.md. Sections appear only where
    the format forces them (several accounts, several memory fields). Reconciles
    rather than wiping (reconcile_dir): a deposit's markdown never changes once
    written, so a re-run rewrites nothing — silence on disk, no iCloud churn."""
    files = {}
    for f in deposits:
        accounts = json.loads(f.read_text())
        out = [f'# Claude memory — {f.stem}', '']
        for a in accounts:
            if len(accounts) > 1:
                out += [f'## account {a.get("account_uuid", "?")[:8]}', '']
            fields = {k: v for k, v in a.items() if k != 'account_uuid'}
            for name, value in sorted(fields.items()):
                if len(fields) > 1:
                    out += [f'## {name}', '']
                out += [str(value).rstrip(), '']
        files[f'{f.stem}.md'] = '\n'.join(out).rstrip() + '\n'
    w, u, r = reconcile_dir(out_dir, files)
    shown = out_dir.relative_to(REPO) if out_dir.is_relative_to(REPO) else out_dir
    print(f'{len(deposits)} memory snapshot(s) to {shown} — {w} written, {u} unchanged, {r} pruned')


def status(memories_output: Path, chat_exports_cache: Path) -> int:
    """The bare-noun default: show current state, write nothing. Reports how many
    deposits the store already holds and how many memory states sit in the cache
    awaiting a sync."""
    n = len(list(memories_output.glob('*.json'))) if memories_output.is_dir() else 0
    states = memory_states(chat_exports_cache)
    store = memories_output.relative_to(REPO) if memories_output.is_relative_to(REPO) else memories_output
    print(f'memories: {n} deposit(s) in {store}; {len(states)} memory state(s) in the cache')
    return 0


def sync(chat_exports_cache: Path, memories_output: Path, markdown: Path) -> int:
    """The verb: deposit every distinct chat-memory state verbatim into the durable
    store (content-deduplicated against the nearest earlier deposit; deposits are
    immutable and outlive their batches), then render the diffable markdown timeline.
    Free, local, idempotent (L1) — the only path here that writes."""
    states = memory_states(chat_exports_cache)
    if not states:
        print(f'no archived memory states under {chat_exports_cache} — nothing to accumulate')
        return 0
    deposits, conflicts = deposit(states, memories_output)
    render(deposits, markdown)
    return 1 if conflicts else 0


def main():
    ap = argparse.ArgumentParser(
        description='The durable chat-memory store. Bare shows status; `sync` deposits '
                    'every distinct state (immutable, content-deduplicated) and renders the '
                    'markdown timeline — free, local, idempotent.')
    sub = ap.add_subparsers(dest='verb')
    sub.add_parser('sync')
    args = ap.parse_args()
    if args.verb == 'sync':
        return sync(CHAT_EXPORTS_CACHE_DIR, MEMORIES_OUTPUT_DIR, MARKDOWN_DIR)
    # bare → status (read-only), against the canonical store
    return status(MEMORIES_OUTPUT_DIR, CHAT_EXPORTS_CACHE_DIR)


if __name__ == '__main__':
    sys.exit(main())
