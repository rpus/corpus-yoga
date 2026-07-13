#!/usr/bin/env python
"""
accumulate_summaries.py — deposit every distinct conversation summary durably.

The summary is a per-snapshot oracle READING of a conversation (a nondeterministic
emission: the same transcript has been observed to re-read differently — №99,
two exports ten hours apart, identical updated_at), carried by every bulk export
and every browser capture, and lossy between snapshots: the backend regenerates it
at will, exports supersede each other, captures refresh in place. Like the
chat-memory document (accumulate_memories.py — whose pattern this repeats per
conversation), each distinct reading is deposited once, durably, so batches and
captures may churn while no reading is ever lost — and compare_batches' summaries
component recognises the deposits as its unconditional licence.

Layout (output/markdown/claude/summaries/):
  <conversation-stem>/          # stem matches output/markdown/claude/conversations/<stem>.md;
                                # renamed when ordinals renumber (the index's uuid is the key)
    index.md                    # the map: uuid, conversation link, one line per reading
    <export-ts>.md              # a distinct reading, verbatim, named by the FIRST export
                                # exhibiting it (ts format matches output/memories deposits)
    browser-capture.md          # the capture's reading, only while it matches no export
                                # deposit (rolling: recaptures refresh it; the export
                                # deposits are the immutable record)

Readings are content-deduplicated against the nearest earlier deposit (memories
semantics); an <export-ts>.md, once written, is never modified. Everything derives
from the local corpora — L1: re-running is silence on disk.

Usage:
  src/run_python_script.sh src/main/chat-exports/accumulate_summaries.py \\
      [--chat-exports-cache cache/chat-exports] [--captures input/browser-captures/claude] \\
      [--conversations-output output/markdown/claude/conversations] \\
      [--summaries-output output/markdown/claude/summaries]
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import REPO, find_api_json

from compare_batches import batch_time  # noqa: E402 — the one batch-ordering authority


def _ts(batch_name):
    """The batch's snapshot time in the output/memories deposit style (compact UTC)."""
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
    deduplicated against the nearest earlier reading (memories semantics) — each
    surviving pair is one distinct reading, stamped with the FIRST batch exhibiting it."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chat-exports-cache', default=str(REPO / 'cache' / 'chat-exports'))
    ap.add_argument('--captures', default=str(REPO / 'input' / 'browser-captures' / 'claude'))
    ap.add_argument('--conversations-output',
                    default=str(REPO / 'output' / 'markdown' / 'claude' / 'conversations'))
    ap.add_argument('--summaries-output',
                    default=str(REPO / 'output' / 'markdown' / 'claude' / 'summaries'))
    args = ap.parse_args()

    root = Path(args.summaries_output)
    stems = stems_by_uuid(Path(args.conversations_output))
    readings = readings_by_uuid(Path(args.chat_exports_cache))
    captured = capture_summaries(Path(args.captures))

    # existing folders by their index's uuid — the rename key across renumberings
    existing = {}
    if root.is_dir():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            idx = d / 'index.md'
            if idx.exists():
                m = re.search(r'^uuid: ([0-9a-f-]{36})$', idx.read_text()[:300], flags=re.M)
                if m:
                    existing[m.group(1)] = d

    deposited = unchanged = renamed = 0
    for u in sorted(set(readings) | set(captured)):
        stem, title = stems.get(u, (None, None))
        if stem is None:
            # never captured: name by the newest batch's piece carrying it
            stem = title = next((f.stem for b in sorted(Path(args.chat_exports_cache).glob('data-*'),
                                                        key=lambda d: d.name, reverse=True)
                                 for f in (b / 'json').glob('*.json')
                                 if u in f.read_text()), u[:8])
        folder = root / stem
        prior = existing.get(u)
        if prior is not None and prior != folder:
            prior.rename(folder)   # presentation renumbered; the deposit follows its conversation
            renamed += 1
        folder.mkdir(parents=True, exist_ok=True)

        texts = []
        for ts, s in readings.get(u, []):
            f = folder / f'{ts}.md'
            if not f.exists():
                f.write_text(s)          # verbatim — the deposit IS the reading
                deposited += 1
            elif f.read_text() != s:
                print(f'  WARN {stem}/{ts}.md: existing deposit differs from this derivation — '
                      'left untouched (deposits are immutable)', file=sys.stderr)
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
          f'{renamed} folder(s) renamed -> {root.relative_to(REPO) if root.is_relative_to(REPO) else root}')


if __name__ == '__main__':
    main()
