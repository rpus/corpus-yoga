#!/usr/bin/env python
"""
files_from_downloaded.py

Produces a data-files JSON table from the lib/artifacts/downloaded/ directory,
one row per file per chat. Used by present.sh to drive the index.html tooltip.

Using downloaded as the source (rather than local_resource tool-result records
from conversations.json) gives a pre-curated, de-duplicated, path-consistent
view: the downloaded directory already resolves all container-path nonsense
and multiple-version noise upstream.

The library directories are keyed "<ordinal>-<slug>-<uuid8>" (identity, renumbering-proof
— see library.py); the presentation tables speak ordinals. This tool performs
the identity→presentation join: the uuid8 suffix of each library directory is
looked up in data-chats.json (whose uuid column comes from the one naming
authority, markdown_projection.ordered()) to recover the batch's CURRENT
ordinal. A library directory whose conversation is not in this batch (deleted
live, or captured-only) is reported on stderr and omitted — never mis-numbered.

Output columns: ["chat", "file"]
  chat  The conversation's 1-based ordinal in this batch, so it joins to
        data-chats.chat / the atomised json/<ordinal>-<slug>.json filenames.
  file  Path relative to the chat directory, as stored in downloaded/.

Usage (called by present.sh):
    python files_from_downloaded.py <downloaded-dir> <data-chats.json>

Output is JSON written to stdout; pipe through format_table.py as normal.
"""

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(f'Usage: {sys.argv[0]} <downloaded-dir> <data-chats.json>')

    downloaded_dir = Path(sys.argv[1])
    if not downloaded_dir.exists():
        # No downloaded files at all — produce an empty table.
        print(json.dumps({'columns': ['chat', 'file'], 'rows': []}))
        return

    chats = json.loads(Path(sys.argv[2]).read_text())
    ci = {c: i for i, c in enumerate(chats['columns'])}
    ordinal_by_uuid8 = {row[ci['uuid']][:8]: row[ci['chat']] for row in chats['rows']}

    rows: list[list[int | str]] = []
    for chat_dir in sorted(downloaded_dir.iterdir()):
        if not chat_dir.is_dir():
            continue
        # "<ordinal>-<slug>-<uuid8>" (see library.py); the prefix fallback reads the
        # legacy uuid8-first vintage, present until a pipeline run touch-heals it
        uuid8 = chat_dir.name.rsplit('-', 1)[-1]
        chat_idx = ordinal_by_uuid8.get(uuid8)
        if chat_idx is None:
            chat_idx = ordinal_by_uuid8.get(chat_dir.name.split('-', 1)[0])
        if chat_idx is None:
            print(f'files_from_downloaded: {chat_dir.name} not in this batch — omitted',
                  file=sys.stderr)
            continue
        for f in sorted(chat_dir.rglob('*')):
            if f.is_file() and f.name != '.DS_Store':
                rows.append([chat_idx, str(f.relative_to(chat_dir))])

    rows.sort()
    print(json.dumps({'columns': ['chat', 'file'], 'rows': rows}))


if __name__ == '__main__':
    main()
