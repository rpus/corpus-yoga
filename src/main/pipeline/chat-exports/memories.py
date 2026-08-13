#!/usr/bin/env python
"""
memories.py — accumulate every distinct chat-memory state into the
durable library, and project the accumulated timeline to markdown.

Bulk exports are the ONLY log of chat memories, and the memory document is a
mutable rolling summary — rewritten, and lossy, between exports. Conversations
accumulate by uuid (identity stable, ordinals drift); memory snapshots are
versions of ONE document, so here snapshot time IS the identity — the dual
keying (cf. library.py):

    data/output/memories/<batch snapshot time, ISO-8601 UTC>.json   (verbatim memories.json)

Per pipeline run, every batch's archived memory state (tmp/cache/<batch>/memories/,
written by archive_components.py) is deposited under its batch timestamp unless
the nearest earlier deposit already carries identical content — so an unchanged
memory costs nothing, a rewrite is preserved forever, and a reverted-then-back
document redeposits honestly. Deposits are never modified or removed; they
outlive their batches, which is the point: once a batch's memory state is
deposited, the batch's memories-divergence no longer blocks its deletion
(supersede stays unprejudiced — the deposit report here is the licence,
not a carve-out there).

The projection renders every deposit to data/output/markdown/claude/chat/memories/<stamp>.md (this
stage owns that subtree). The memory content is already markdown inside the
JSON string, so this is an unwrap, not a transformation — the served corpus
gains a diffable timeline of what claude.ai believed about the user at each
export.

Usage (wired into src/main/cli/pipeline/pipeline.sh after the per-batch stages):
    src/run_python_script.sh src/main/pipeline/chat-exports/memories.py \
      [--chat-exports-cache tmp/cache/chat-exports] [--memories-output data/output/memories] \
      [--markdown data/output/markdown/claude/chat/memories]
"""
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from supersede import batch_time
from accumulate import accumulate  # the one deposit rule (issue #22)

SELF = 'src/main/pipeline/chat-exports/memories.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src'))  # src/ — modules both tiers import
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main'))  # src/main/ on the path
# renamed on import: this file's own deposit() puts memory STATES into the
# library; the shared one puts rendered FILES into a directory (#426)
from markdown_projection import deposit as deposit_files  # noqa: E402
from declared_parser import command_parser  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[3]


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
    identical, via the shared CALCULUS accumulate rule (accumulate.py). Existing
    deposits are immutable; a same-stamp content mismatch is a CONFLICT, reported
    loudly and left alone. normalise_stamps first heals legacy filenames so the
    stamp comparison sees one vintage."""
    lib_dir.mkdir(parents=True, exist_ok=True)
    conflicts = normalise_stamps(lib_dir)
    for stamp, batch, text in states:
        result = accumulate(lib_dir, stamp, text, suffix='.json')
        if result == 'conflict':
            conflicts += 1
            status = '✗ CONFLICT: deposit exists with different content — investigate'
        elif result == 'deposited':
            status = '✓ deposited (new)'
        else:
            status = 'unchanged — no new deposit'
        print(f'  {batch}: memory state {stamp} {status}')
    deposits = sorted(lib_dir.glob('*.json'))
    print(f'data/output/memories: {len(deposits)} deposit(s)')
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
    deposit_files(out_dir, files, f'{len(deposits)} memory snapshot(s)',
                  because='its deposit is gone')


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
    args = command_parser('memories').parse_args()  # whole surface declared (#476, #477)
    if args.verb == 'sync':
        return sync(Path(args.chat_exports_cache), Path(args.memories_output), Path(args.markdown))
    # bare → status (read-only)
    return status(Path(args.memories_output), Path(args.chat_exports_cache))


if __name__ == '__main__':
    sys.exit(main())
