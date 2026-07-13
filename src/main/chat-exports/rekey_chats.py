#!/usr/bin/env python
"""
rekey_chats.py — swap a table's chat-identity column between ordinal and id.

A stdin→stdout filter for tables whose rows reference conversations (e.g. the
captured data-chat-categories). Ordinals are presentation, ids are identity —
the source-native conversation id: claude's uuid, gemini's 16-hex app id (no
uuids exist there; conv_id extracts both uniformly). The LLM speaks ordinals
(short, reliable in a prompt), durable storage (output/dashboard/) speaks id
(renumbering-proof), and presentation re-derives ordinals at injection time.
The ordinal↔id mapping comes from the ordering authority given to
--conversations (see _order).

  --to-id       rows carry a 'chat' ordinal column  → rewrite as 'id'
  --to-ordinal  rows carry an 'id' column           → rewrite as 'chat' ordinal

Rows whose conversation is unknown to the corpus (a stale uuid after a live
deletion, an ordinal the LLM hallucinated) are dropped with a note on stderr —
a durable table must never carry a dangling reference forward silently.

--legacy-ordinals (with --to-id only): interpret incoming ordinals under the
numbering ordered() produced before empty stubs were excluded (924ebf8) — the
1-based, all-inclusive numbering that inferred tables from the 924ebf8..a19be50
era were generated against. NOT the era before 3b8faba (Jul 2), when
infer_tables.sh (dashboard.sh's predecessor) numbered chats itself via jq
to_entries: 0-BASED, created_at
only — a table from that vintage migrated with this flag mis-assigns every row
by one, and only the dropped 'chat 0' would hint at it. None survive on disk,
but check the provenance before trusting the flag on an unfamiliar table.
This is the migration recipe for an old ordinal-keyed inferred table:

    src/main/chat-exports/rekey_chats.py --to-id --legacy-ordinals \\
        --conversations <batch>/conversations.json \\
        < cache/chat-exports/<batch>/inferred/data-chat-categories.json

Usage (see dashboard.sh / present.sh):
    ... | rekey_chats.py --to-id --conversations <corpus dir | conversations.json> | ...
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import is_empty, ordered, load_convs, corpus_index


def _order(conversations, legacy):
    """[(ordinal, id)] from the ordering authority — either a projected corpus
    (a conversations dir, or the output/markdown root combining every source: the
    filenames ARE the cached ordering, read back by corpus_index) or a batch's
    conversations.json / atomised json/ (re-derived via ordered())."""
    p = Path(conversations)
    if p.is_dir() and (any(p.glob('*.md')) or any(p.glob('*/conversations/*.md'))):
        if legacy:
            sys.exit('rekey_chats: --legacy-ordinals needs a batch source '
                     '(conversations.json or json/), not a markdown corpus dir')
        return [(n, u) for n, _stem, _title, u in corpus_index(p)]
    convs = load_convs(conversations)
    if legacy:
        # The numbering ordered() produced before 924ebf8: same (created_at, uuid) sort,
        # but empty stubs counted. A stub takes its ordinal yet gets no mapping entry, so
        # its rows drop with the standard note — a category for a content-free chat
        # carries nothing worth migrating.
        by_created = sorted(convs, key=lambda c: (c['created_at'], c['uuid']))
        return [(i, c['uuid']) for i, c in enumerate(by_created, 1) if not is_empty(c)]
    return [(n, c['uuid']) for n, _, c in ordered(convs) if n is not None]


def main():
    ap = argparse.ArgumentParser()
    direction = ap.add_mutually_exclusive_group(required=True)
    direction.add_argument('--to-id', action='store_true')
    direction.add_argument('--to-ordinal', action='store_true')
    ap.add_argument('--conversations', required=True,
                    help='the ordering authority: the projected corpus (a conversations '
                         'dir or the output/markdown root), a batch conversations.json, or '
                         'an atomised json/ dir')
    ap.add_argument('--legacy-ordinals', action='store_true',
                    help='incoming ordinals counted empty stubs (pre-924ebf8 numbering); '
                         'for migrating old inferred tables')
    args = ap.parse_args()
    if args.legacy_ordinals and not args.to_id:
        ap.error('--legacy-ordinals is a migration aid: legacy ordinals only ever come IN, '
                 'so it requires --to-id')

    order = _order(args.conversations, args.legacy_ordinals)
    table = json.load(sys.stdin)

    old_col, new_col = ('chat', 'id') if args.to_id else ('id', 'chat')
    mapping: dict[int | str, int | str] = (
        {n: u for n, u in order} if args.to_id
        else {u: n for n, u in order})
    ci = {c: i for i, c in enumerate(table['columns'])}
    if old_col not in ci:
        sys.exit(f"rekey_chats: no '{old_col}' column in {table['columns']}")

    kept, dropped = [], []
    for row in table['rows']:
        key = row[ci[old_col]]
        if args.to_id and isinstance(key, str) and key.strip().isdigit():
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
