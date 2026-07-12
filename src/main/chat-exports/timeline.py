#!/usr/bin/env python
"""
timeline.py — emit the presentation's conversation-keyed tables from a bulk export's
conversations.json, plus the numbered chat list for inference. Every table's `chat` value comes
from the one canonical ordering in markdown_projection.ordered() (created_at order, 1-based), so
the timeline number, the atomised json/<ordinal>-<slug>.json filename, and the inferred
category joins all agree. Replaces the inline jq that present.sh and infer_tables.sh
(dashboard.sh's predecessor) used to duplicate.

`chat` is the 1-based ordinal, kept as an integer so index.html's JS joins (spans/categories/files
→ conversation) stay numeric; the zero-padded form is the filename only.

Usage:
  src/run_python_script.sh src/main/chat-exports/timeline.py <conversations.json> --table chats
    --table chats            -> {columns:[chat,name,dormant_from,uuid], rows:[...]}  (data-chats)
    --table spans            -> {columns:[chat,from,to,messages],  rows:[...]}   (data-spans)
    --table local-resources  -> {columns:[chat,file,mime_type],    rows:[...]}   (data-local-resources)
    --table chat-list         -> "<n>: <name>" lines (stdin for the inference API)
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import ordered, load_convs

OUTPUTS_PREFIX = '/mnt/user-data/outputs/'


def _trim(ts):
    """Drop sub-second precision: '…:19.633978Z' -> '…:19Z' (matches the old jq sub())."""
    return re.sub(r'\.[0-9]+Z$', 'Z', ts) if ts else ts


def chats(order):
    # uuid is the conversation's durable identity — the join key to the uuid8-keyed
    # stores (lib/artifacts/downloaded/, inferred tables); chat is only its CURRENT
    # ordinal in this batch. source/channel are constant here by CONSTRUCTION: a
    # batch is a claude.ai bulk export, so every row is claude × chat — stated
    # explicitly so the dashboard never has to guess provider from the id shape
    # (which a 36-char code-session uuid would fool). Consumers read columns by
    # name, so extra columns are invisible to the dashboard timeline itself.
    return {'columns': ['chat', 'name', 'dormant_from', 'uuid', 'provider', 'channel', 'turns'],
            'rows': [[n, c['name'], _trim(c.get('updated_at')), c['uuid'], 'claude', 'chat',
                      len(c['chat_messages'])]
                     for n, _, c in order]}


def spans(order):
    """Runs of consecutive (in global time order) messages belonging to the same conversation."""
    events = [{'chat': n, 'from': _trim(m['created_at']), 'to': _trim(m['created_at'])}
              for n, _, c in order for m in c['chat_messages']]
    events.sort(key=lambda e: e['from'])
    merged = []
    cur = None
    for e in events:
        if cur is not None and cur['chat'] == e['chat']:
            cur['to'] = e['to']
            cur['messages'] += 1
        else:
            cur = {'chat': e['chat'], 'from': e['from'], 'to': e['from'], 'messages': 1}
            merged.append(cur)
    return {'columns': ['chat', 'from', 'to', 'messages'],
            'rows': [[s['chat'], s['from'], s['to'], s['messages']] for s in merged]}


def local_resources(order):
    rows = set()
    for n, _, c in order:
        for m in c['chat_messages']:
            for blk in m.get('content', []):
                if blk.get('type') != 'tool_result':
                    continue
                for item in (blk.get('content') or []):
                    if isinstance(item, dict) and item.get('type') == 'local_resource':
                        fp = item.get('file_path', '')
                        if fp.startswith(OUTPUTS_PREFIX):
                            fp = fp[len(OUTPUTS_PREFIX):]
                        rows.add((n, fp, item.get('mime_type')))
    return {'columns': ['chat', 'file', 'mime_type'], 'rows': [list(r) for r in sorted(rows)]}


def chat_list(order):
    return '\n'.join(f'{n}: {c["name"]}' for n, _, c in order)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('conversations',
                    help='a bulk export conversations.json OR an atomised json/ dir')
    ap.add_argument('--table', required=True,
                    choices=['chats', 'spans', 'local-resources', 'chat-list'])
    args = ap.parse_args()

    order = ordered(load_convs(args.conversations))
    order = [t for t in order if t[0] is not None]  # empty stubs have no ordinal and no timeline presence
    if args.table == 'chat-list':
        print(chat_list(order))
    else:
        fn = {'chats': chats, 'spans': spans, 'local-resources': local_resources}[args.table]
        print(json.dumps(fn(order), ensure_ascii=False))


if __name__ == '__main__':
    main()
