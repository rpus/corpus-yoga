#!/usr/bin/env python
"""
rekey_chats.py — swap a table's chat-identity column between ordinal and uuid.

A stdin→stdout filter for tables whose rows reference conversations (e.g. the
inferred data-chat-categories). Ordinals are presentation, uuids are identity:
the LLM speaks ordinals (short, reliable in a prompt), durable storage under
inferred/ speaks uuid (renumbering-proof), and presentation re-derives ordinals
at injection time. The ordinal↔uuid mapping comes from the one naming authority,
markdown_projection.ordered(), over the batch's conversations.json.

  --to-uuid     rows carry a 'chat' ordinal column  → rewrite as 'uuid'
  --to-ordinal  rows carry a 'uuid' column          → rewrite as 'chat' ordinal

Rows whose conversation is unknown to the corpus (a stale uuid after a live
deletion, an ordinal the LLM hallucinated) are dropped with a note on stderr —
a durable table must never carry a dangling reference forward silently.

Usage (see infer_tables.sh / present.sh):
    ... | rekey_chats.py --to-uuid --conversations <conversations.json> | ...
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import ordered


def main():
    ap = argparse.ArgumentParser()
    direction = ap.add_mutually_exclusive_group(required=True)
    direction.add_argument('--to-uuid', action='store_true')
    direction.add_argument('--to-ordinal', action='store_true')
    ap.add_argument('--conversations', required=True,
                    help='the batch conversations.json (ordering authority)')
    args = ap.parse_args()

    order = [(n, c) for n, _, c in ordered(json.loads(Path(args.conversations).read_text()))
             if n is not None]
    table = json.load(sys.stdin)

    old_col, new_col = ('chat', 'uuid') if args.to_uuid else ('uuid', 'chat')
    mapping: dict[int | str, int | str] = (
        {n: c['uuid'] for n, c in order} if args.to_uuid
        else {c['uuid']: n for n, c in order})
    ci = {c: i for i, c in enumerate(table['columns'])}
    if old_col not in ci:
        sys.exit(f"rekey_chats: no '{old_col}' column in {table['columns']}")

    kept, dropped = [], []
    for row in table['rows']:
        key = row[ci[old_col]]
        if args.to_uuid and isinstance(key, str) and key.strip().isdigit():
            key = int(key.strip())
        if key in mapping:
            row = list(row)
            row[ci[old_col]] = mapping[key]
            kept.append(row)
        else:
            dropped.append(row)

    for row in dropped:
        print(f'rekey_chats: dropped row with unknown {old_col} {row[ci[old_col]]!r}',
              file=sys.stderr)
    table['columns'] = [new_col if c == old_col else c for c in table['columns']]
    table['rows'] = kept
    json.dump(table, sys.stdout, indent=2)
    print()


if __name__ == '__main__':
    main()
