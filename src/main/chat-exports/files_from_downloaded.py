#!/usr/bin/env python
"""
files_from_downloaded.py

Produces a data-files JSON table from the lib/artifacts/downloaded/ directory,
one row per file per chat. Used by present.sh to drive the index.html tooltip.

Using downloaded as the source (rather than local_resource tool-result records
from conversations.json) gives a pre-curated, de-duplicated, path-consistent
view: the downloaded directory already resolves all container-path nonsense
and multiple-version noise upstream.

Output columns: ["chat", "file"]
  chat  The conversation's 1-based ordinal (the canonical numbering from
        markdown_projection.ordered() — created_at order), so it joins to
        data-chats.chat / the atomised json/<ordinal>-<slug>.json filenames.
        Derived from the leading "<ordinal>-" in the directory name, which
        follows that same convention, e.g. "16-accessing_files..." -> 16.
  file  Path relative to the chat directory, as stored in downloaded/.

Usage (called by present.sh):
    python files_from_downloaded.py <downloaded-dir>

Output is JSON written to stdout; pipe through format_table.py as normal.
"""

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f'Usage: {sys.argv[0]} <downloaded-dir>')

    downloaded_dir = Path(sys.argv[1])
    if not downloaded_dir.exists():
        # No downloaded files at all — produce an empty table.
        print(json.dumps({'columns': ['chat', 'file'], 'rows': []}))
        return

    rows: list[list[int | str]] = []
    for chat_dir in sorted(downloaded_dir.iterdir()):
        if not chat_dir.is_dir():
            continue
        prefix = chat_dir.name.split('-', 1)[0]  # "<ordinal>-<slug>" (canonical, 1-based)
        if not prefix.isdigit():
            continue
        chat_idx = int(prefix)
        for f in sorted(chat_dir.rglob('*')):
            if f.is_file() and f.name != '.DS_Store':
                rows.append([chat_idx, str(f.relative_to(chat_dir))])

    print(json.dumps({'columns': ['chat', 'file'], 'rows': rows}))


if __name__ == '__main__':
    main()
