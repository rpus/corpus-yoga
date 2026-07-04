#!/usr/bin/env python
"""
compare_batches.py — do later bulk exports SUPERSEDE earlier ones?

Conversations are append-only, so an earlier export's data should be a subset of the
latest export's: every conversation still present, every message uuid still present.
Checked on the RAW atomised json/ pieces — format-agnostic (message uuids exist in
every export vintage), so an old batch's schema conformance and projectability are
irrelevant to the data question.

Per earlier batch, against the LATEST batch:
  subset    — every message uuid of every conversation is present in its later self
  ORPHANED  — a conversation absent from the latest export (deleted on claude.ai):
              the earlier batch holds unique data
  ANOMALY   — messages present earlier but missing later: should be impossible for
              an append-only tree; investigate before trusting either batch

Overall: if every earlier batch is fully superseded, the latest snapshot is
SUFFICIENT and the earlier batches are deletable — validation matrices are
machine-local and die with their data, and the committed CHANGELOG narratives
keep the history.

Usage:
  src/run_python_script.sh src/main/chat-exports/compare_batches.py \
    [--chat-exports-gen gen/chat-exports]

Requires the batches' atomised json/ (written by the chat-exports pipeline).
Exit 0 iff the latest snapshot is sufficient.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def batch_time(name):
    m = re.search(r'-(\d{10})-[0-9a-f]+-batch', name)
    if m:
        return datetime.fromtimestamp(int(m.group(1)), tz=timezone.utc)
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})', name)
    if m:
        return datetime(*map(int, m.groups()), tzinfo=timezone.utc)
    return None


def load_batch(json_dir):
    """{conversation uuid: set of message uuids}, plus {uuid: piece filename stem}."""
    convs, names = {}, {}
    for f in sorted(json_dir.glob('*.json')):
        c = json.load(f.open())
        u = c.get('uuid')
        if not u:
            continue
        convs[u] = {m['uuid'] for m in c.get('chat_messages', []) if m.get('uuid')}
        names[u] = f.stem
    return convs, names


def load_captures(captures_dir):
    """{conversation uuid: set of message uuids} (+ names) from <uuid>/<uuid>.json captures."""
    convs, names = {}, {}
    for d in sorted(captures_dir.iterdir()):
        j = d / f'{d.name}.json' if d.is_dir() else None
        if j and j.exists():
            c = json.load(j.open())
            u = c.get('uuid', d.name)
            convs[u] = {m['uuid'] for m in c.get('chat_messages', []) if m.get('uuid')}
            names[u] = c.get('name', '')
    return convs, names


def compare_vs_captures(latest, latest_convs, latest_names, captures_dir):
    """Directional per-conversation supersession between the latest bulk export and the
    live-capture corpus (the data frontier). Informational: capture-ahead is the normal
    post-snapshot direction; capture-stale names conversations to recapture in place;
    an anomaly (unique messages on BOTH sides) wants investigation."""
    caps, cap_names = load_captures(captures_dir)
    shared = set(latest_convs) & set(caps)
    in_sync = ahead = 0
    stale, anomalies = [], []
    for u in sorted(shared):
        b, c = latest_convs[u], caps[u]
        if b == c:
            in_sync += 1
        elif b < c:
            ahead += 1
        elif c < b:
            stale.append(u)
        else:
            anomalies.append(u)
    export_only = sorted(set(latest_convs) - set(caps))
    capture_only = sorted(set(caps) - set(latest_convs))
    print(f'{latest.name} vs captures: {len(shared)} shared — {in_sync} in-sync, '
          f'{ahead} capture-ahead, {len(stale)} capture-stale, {len(anomalies)} anomalies; '
          f'{len(export_only)} export-only (deleted live?), '
          f'{len(capture_only)} capture-only (post-export)')
    for u in export_only:
        print(f'  EXPORT-ONLY {latest_names.get(u, u)} ({u}): deleted live? the export holds its only copy')
    for u in capture_only:
        print(f'  capture-only {cap_names.get(u, "")!r} ({u}): post-export — the next export will include it')
    for u in stale:
        print(f'  CAPTURE-STALE {u}: the export holds {len(latest_convs[u] - caps[u])} message(s) '
              f'the capture lacks — recapture in place')
    for u in anomalies:
        print(f'  ANOMALY {u}: unique messages on both sides — investigate')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chat-exports-gen', default='gen/chat-exports',
                    help='gen root holding <batch>/json/ atomised pieces')
    ap.add_argument('--captures', default=None,
                    help='ext/browser-captures/claude — also compare the latest batch '
                         'against the live-capture corpus, per conversation (informational)')
    args = ap.parse_args()

    root = Path(args.chat_exports_gen)
    batches = sorted((d for d in root.glob('data-*') if (d / 'json').is_dir()),
                     key=lambda d: (batch_time(d.name) or datetime.min.replace(tzinfo=timezone.utc)))
    unparseable = [d.name for d in batches if batch_time(d.name) is None]
    for n in unparseable:
        print(f'warning: cannot parse a time from batch name {n} — ordering may be wrong', file=sys.stderr)
    if not batches:
        print(f'no batches with atomised json/ under {root} — nothing to compare')
        return 0

    latest = batches[-1]
    latest_convs, latest_names = load_batch(latest / 'json')
    if len(batches) < 2:
        print(f'1 batch with atomised json/ under {root} — no earlier batches to compare')
    else:
        print(f'latest: {latest.name} ({len(latest_convs)} conversations, '
              f'{sum(len(v) for v in latest_convs.values())} messages)')

    sufficient = True
    for b in batches[:-1]:
        convs, names = load_batch(b / 'json')
        subset = orphaned = anomalies = 0
        details = []
        for u, msgs in sorted(convs.items()):
            if u not in latest_convs:
                orphaned += 1
                details.append(f'  ORPHANED {names[u]} ({u}): {len(msgs)} messages absent from latest')
            elif msgs <= latest_convs[u]:
                subset += 1
            else:
                anomalies += 1
                missing = len(msgs - latest_convs[u])
                details.append(f'  ANOMALY {names[u]} ({u}): {missing} message(s) present here, missing in latest')
        verdict = 'SUPERSEDED' if not (orphaned or anomalies) else 'NOT superseded'
        print(f'{b.name}: {len(convs)} conversations — {subset} subset, '
              f'{orphaned} orphaned, {anomalies} anomalies → {verdict}')
        for d in details:
            print(d)
        sufficient = sufficient and not (orphaned or anomalies)

    if len(batches) >= 2:
        print(f'verdict: latest snapshot is {"SUFFICIENT — earlier batch(es) deletable" if sufficient else "NOT sufficient — earlier batch(es) hold unique data"}')

    if args.captures and Path(args.captures).is_dir():
        compare_vs_captures(latest, latest_convs, latest_names, Path(args.captures))

    return 0 if sufficient else 1


if __name__ == '__main__':
    sys.exit(main())
