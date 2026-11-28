"""
render.py - render each conversation of one bulk-export batch, a map (issues/1196): each atomised
piece's markdown body under the piece's name, and the facts the collate dresses it by, written
at the batch's cache address, so that the collate reads them and never the pieces.

Usage:
  src/run_python_script.sh src/main/export/render.py --bulk-export data/input/claude/chat/bulk-export/<batch>
"""
import argparse
import json
import sys
from pathlib import Path
import tier
from markdown_projection import FACTS, RENDERINGS, facts, md_validator, project, render_body, write_if_changed



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--bulk-export', required=True, help='a bulk-export batch dir whose atomised json/ pieces are rendered')
    args = ap.parse_args()
    cache = tier.cache_of(Path(args.bulk_export))
    pieces = sorted((cache / 'json').glob('*.json'))
    if not pieces:
        sys.exit(f"no atomised json/ at {cache / 'json'}; atomise_bulk.py --bulk-export {args.bulk_export} writes it")
    valid = md_validator()
    record, written, removed = {}, 0, 0
    for piece in pieces:
        conversation = json.loads(piece.read_text())
        record[piece.stem] = facts(conversation, valid)
        written += write_if_changed(cache / RENDERINGS / f'{piece.stem}.md', render_body(project(conversation)))
    # the pieces renumber as a batch's ordering does; a rendering no piece names is gone
    for stale in (cache / RENDERINGS).glob('*.md'):
        if stale.stem not in record:
            stale.unlink()
            removed += 1
    write_if_changed(cache / FACTS, json.dumps(record, ensure_ascii=False, indent=1) + '\n')
    print(f'  render: {len(pieces)} conversation(s), {written} rendered anew, {len(pieces) - written} current, {removed} removed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
