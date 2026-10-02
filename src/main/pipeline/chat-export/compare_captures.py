#!/usr/bin/env python
"""
compare_captures.py - the latest bulk export against the API captures, per conversation:
a step of the chat-export run's tail, informational, never a command.

Directional per-conversation comparison between the latest export and the live-capture
corpus, the data frontier, by message uuids: capture-ahead is the normal post-snapshot
direction; capture-stale names conversations to recapture in place; an anomaly, unique
messages on both sides, wants investigation; an export-only conversation with no message
content is complete as the export holds it and names nothing to capture. Each mismatch is
its own FAIL atom, counted by the run's stage table (#446) and never a gate.

Usage:
  src/run_python_script.sh src/main/pipeline/chat-export/compare_captures.py --api-capture <root>
"""
import argparse
import json
import sys
from pathlib import Path

SELF = 'src/main/pipeline/chat-export/compare_captures.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
sys.path.insert(0, str(REPO / 'src' / 'main'))
sys.path.insert(0, str(_file.parent))
import tier  # noqa: E402 - the tiers, one home (#702)
import atoms  # noqa: E402 - the export's conversations and their atoms, one home (#743)
from vintage import export_time  # noqa: E402 - the one export-ordering authority

BULK = 'data/input/claude/chat/bulk-export'


def latest_export() -> Path | None:
    """The newest export the store holds, by its name's vintage."""
    root = tier.path(BULK)
    exports = sorted((d for d in root.glob('data-*') if (d / 'conversations.json').is_file()),
                     key=lambda d: export_time(d.name) or 0) if root.is_dir() else []
    return exports[-1] if exports else None


def captures(root: Path) -> tuple[dict, dict]:
    """{conversation uuid: {message uuids}} and {uuid: name} from <uuid>/<uuid>.json captures."""
    convs, names = {}, {}
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        j = d / f'{d.name}.json' if d.is_dir() else None
        if j and j.exists():
            c = json.loads(j.read_text())
            u = c.get('uuid', d.name)
            convs[u] = {m['uuid'] for m in c.get('chat_messages', []) if m.get('uuid')}
            names[u] = c.get('name', '')
    return convs, names


def compare(export: Path, captures_root: Path) -> None:
    held = {c['uuid']: c for c in atoms._conversations(export) if c.get('uuid')}
    mine = atoms.conversations(export)
    caps, cap_names = captures(captures_root)
    shared = set(mine) & set(caps)
    in_sync = ahead = 0
    stale, anomalies = [], []
    for u in sorted(shared):
        b, c = mine[u][1], caps[u]
        if b == c:
            in_sync += 1
        elif b < c:
            ahead += 1
        elif c < b:
            stale.append(u)
        else:
            anomalies.append(u)
    export_only = sorted(set(mine) - set(caps))
    capture_only = sorted(set(caps) - set(mine))
    print(f'{export.name} vs captures: {len(shared)} shared — {in_sync} in-sync, '
          f'{ahead} capture-ahead, {len(stale)} capture-stale, {len(anomalies)} anomalies; '
          f'{len(export_only)} export-only (no local capture), '
          f'{len(capture_only)} capture-only (absent from this export)')

    def blank(uuid: str) -> bool:
        """No content in any message, a stray blank send: the export's record is complete
        however long it is kept, and nothing is worth capturing."""
        msgs = held.get(uuid, {}).get('chat_messages', [])
        return bool(msgs) and all(not m.get('text') and not m.get('content') for m in msgs)

    for u in export_only:
        if not mine[u][1] or blank(u):
            print(f'  export-only {mine[u][0]} ({u}): blank (no message content) — '
                  'the export holds its complete record; nothing to capture')
            continue
        print(f'FAIL: export-only {mine[u][0]} ({u}) - no capture of it here; to capture:')
        print(f'    → run: corpus-yoga browser capture --provider claude --id {u}'
              f'  # first front https://claude.ai/chat/{u} in Safari (logged in)')
    for u in capture_only:
        print(f'  capture-only {cap_names.get(u, "")!r} ({u}): in the captures, absent from this export')
    for u in stale:
        print(f'FAIL: capture-stale {cap_names.get(u, "")!r} ({u}) - the export holds '
              f'{len(mine[u][1] - caps[u])} message(s) the capture lacks — to recapture:')
        print(f'    → run: corpus-yoga browser capture --provider claude --id {u}'
              f'  # first front https://claude.ai/chat/{u} in Safari (logged in)')
    for u in anomalies:
        print(f'FAIL: anomaly {cap_names.get(u, "")!r} ({u}) - unique messages on both sides - investigate')


def main() -> int:
    parser = argparse.ArgumentParser(prog='compare_captures.py')
    parser.add_argument('--api-capture', required=True, metavar='<root>', help='the API-capture root to compare the latest export against')
    args = parser.parse_args()
    export = latest_export()
    if export is None:
        print(f'compare_captures: no export under {BULK} - nothing to compare')
        return 0
    captures_root = Path(args.api_capture)
    if not captures_root.is_dir():
        print(f'compare_captures: {captures_root} is absent - nothing to compare the export of {export.name} against')
        return 0
    compare(export, captures_root)
    return 0


if __name__ == '__main__':
    sys.exit(main())
