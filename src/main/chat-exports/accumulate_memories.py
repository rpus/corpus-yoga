#!/usr/bin/env python
"""
accumulate_memories.py — accumulate every distinct chat-memory state into the
durable library, and project the accumulated timeline to markdown.

Bulk exports are the ONLY log of chat memories, and the memory document is a
mutable rolling summary — rewritten, and lossy, between exports. Conversations
accumulate by uuid (identity stable, ordinals drift); memory snapshots are
versions of ONE document, so here snapshot time IS the identity — the dual
keying (cf. library.py):

    lib/memories/<batch snapshot time, ISO-8601 UTC>.json   (verbatim memories.json)

Per pipeline run, every batch's archived memory state (gen/<batch>/memories/,
written by archive_components.py) is deposited under its batch timestamp unless
the nearest earlier deposit already carries identical content — so an unchanged
memory costs nothing, a rewrite is preserved forever, and a reverted-then-back
document redeposits honestly. Deposits are never modified or removed; they
outlive their batches, which is the point: once a batch's memory state is
deposited, the batch's memories-divergence no longer blocks its deletion
(compare_batches stays unprejudiced — the deposit report here is the licence,
not a carve-out there).

The projection renders every deposit to lib/markdown/claude/memories/<stamp>.md (this
stage owns that subtree). The memory content is already markdown inside the
JSON string, so this is an unwrap, not a transformation — the served corpus
gains a diffable timeline of what claude.ai believed about the user at each
export.

Usage (wired into RUNME.sh after the per-batch stages):
    src/run_python_script.sh src/main/chat-exports/accumulate_memories.py \
      [--chat-exports-gen gen/chat-exports] [--lib lib/memories] \
      [--markdown lib/markdown/claude/memories]
"""
import argparse
import json
import sys
from datetime import timezone
from pathlib import Path

from compare_batches import batch_time

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]


def memory_states(gen_root):
    """[(stamp, batch name, verbatim text)] for every batch with an archived memory,
    in snapshot-time order."""
    states = []
    for d in sorted(gen_root.glob('data-*')):
        f = d / 'memories' / 'memories.json'
        t = batch_time(d.name)
        if not f.exists() or t is None:
            continue
        stamp = t.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        states.append((stamp, d.name, f.read_text()))
    return sorted(states)


def deposit(states, lib_dir):
    """Deposit each state under its stamp unless the nearest earlier deposit is
    identical. Existing deposits are immutable; a same-stamp content mismatch is
    reported loudly and left alone."""
    lib_dir.mkdir(parents=True, exist_ok=True)
    conflicts = 0
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
    print(f'lib/memories: {len(deposits)} deposit(s)')
    return deposits, conflicts


def render(deposits, out_dir):
    """Unwrap each deposit's markdown to <stamp>.md. Sections appear only where
    the format forces them (several accounts, several memory fields)."""
    import shutil
    if out_dir.exists():
        shutil.rmtree(out_dir)  # this stage owns lib/markdown/claude/memories
    out_dir.mkdir(parents=True, exist_ok=True)
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
        (out_dir / f'{f.stem}.md').write_text('\n'.join(out).rstrip() + '\n')
    shown = out_dir.relative_to(REPO) if out_dir.is_relative_to(REPO) else out_dir
    print(f'rendered {len(deposits)} memory snapshot(s) to {shown}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chat-exports-gen', default=str(REPO / 'gen' / 'chat-exports'))
    ap.add_argument('--lib', default=str(REPO / 'lib' / 'memories'))
    ap.add_argument('--markdown', default=str(REPO / 'lib' / 'markdown' / 'claude' / 'memories'))
    args = ap.parse_args()

    states = memory_states(Path(args.chat_exports_gen))
    if not states:
        print('no archived memory states under '
              f'{args.chat_exports_gen} — nothing to accumulate')
        return 0
    deposits, conflicts = deposit(states, Path(args.lib))
    render(deposits, Path(args.markdown))
    return 1 if conflicts else 0


if __name__ == '__main__':
    sys.exit(main())
