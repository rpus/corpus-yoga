#!/usr/bin/env python
"""
archive_components.py — copy the non-conversation components of a bulk export
(memories.json, projects/, users.json) verbatim into the batch's tmp/cache/ directory.

A bulk export is a synchronised snapshot of FOUR components. The pipeline
derives everything conversations-related into tmp/cache/chat-exports/<batch>/ (json/,
markdown/, extracted_*, presentation/), but the other three components used to
exist only inside data/input/. Copying them beside the derived content makes the cache
batch directory the complete processed record of the snapshot — one root to
read, index, or serve any component — and compare_batches.py reads all four
component loaders from that same root. Copies are byte-verbatim: these are
data, not projections (bulk exports are the only log of chat memories).

    tmp/cache/chat-exports/<batch>/memories/memories.json
    tmp/cache/chat-exports/<batch>/projects/<uuid>.json
    tmp/cache/chat-exports/<batch>/users/users.json

This stage owns those three subtrees (wiped and rewritten each run). A missing
component in the export is reported and skipped, not an error (older export
vintages may lack one).

Usage:
    src/run_python_script.sh src/main/chat-exports/archive_components.py \
      --chat-export data/input/claude/chat/bulk-export/<batch> [--out-dir <override>]
"""
import argparse
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR.parents[2] / 'tmp' / 'cache' / 'chat-exports'

COMPONENTS = ['memories.json', 'projects', 'users.json']


def archive(export_dir: Path, out_dir: Path) -> None:
    copied, absent = [], []
    for name in COMPONENTS:
        src = export_dir / name
        dest = out_dir / src.stem if src.suffix else out_dir / name
        if dest.exists():
            shutil.rmtree(dest)  # this stage owns the three component subtrees
        if not src.exists():
            absent.append(name)
            continue
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / src.name)
        copied.append(name)
    note = f' ({", ".join(absent)} absent in export — skipped)' if absent else ''
    print(f'archived {", ".join(copied) or "nothing"} to {out_dir}{note}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chat-export', required=True)
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    export_dir = Path(args.chat_export).resolve()
    if not export_dir.is_dir():
        sys.exit(f'not a directory: {export_dir}')
    out_dir = Path(args.out_dir) if args.out_dir else CACHE_DIR / export_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    archive(export_dir, out_dir)


if __name__ == '__main__':
    main()
