#!/usr/bin/env python
"""
project_markdown.py — Render conversations to flat markdown, one <name>.md per conversation,
from either source:
  browser-capture  ext/browser-captures/claude/<uuid>/apiConversation.json   (named <ordinal>-<slug>)
  bulk-export      gen/chat-exports/<batch>/json/<name>.json                  (the atomised pieces;
                                                                               run atomise_bulk.py first)

The markdown CLI over the shared primitives in src/main/markdown_projection.py. Markdown is
validated against rsc/schema/browser-captures/markdownConversation/v1.json. Splitting the bulk
array into the per-conversation json/ pieces is atomise_bulk.py's job; this tool only consumes
them, so json/<name>.json and markdown/<name>.md share a name. Nothing is skipped:
invalid/degenerate conversations are rendered honestly and flagged.

Usage (output defaults per pipeline/batch; --out overrides):
  src/run_python_script.sh src/main/model/project_markdown.py \
    --browser-captures ext/browser-captures/claude              # -> gen/markdown/claude/
  src/run_python_script.sh src/main/model/project_markdown.py \
    --bulk-export ext/chat-exports/<batch>                       # -> gen/chat-exports/<batch>/markdown/
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import (REPO, project, ordered, find_api_json, render,
                                 md_validator, tree_problems)


def write_markdown(named_convs, out_dir):
    """Render (name, lean-conv, tree-problems) triples to <name>.md in out_dir, each
    validated against markdownConversation. Nothing skipped -- invalid/degenerate convs
    are written and flagged, with WHY: an unwalkable tree projects to a fragment that
    would otherwise still validate. Returns (n_ok, n_bad)."""
    valid = md_validator()
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)  # renumbering renames files; wipe so no old-naming pieces linger
    out.mkdir(parents=True, exist_ok=True)
    n_ok = n_bad = n_empty = 0
    for name, conv, problems in named_convs:
        if name.startswith('empty-'):
            # ordered() already classified this stub and named it so (the atomised piece
            # stems carry the name to the bulk path) — one authority, no re-deciding here.
            n_empty += 1
            (out / f"{name}.md").write_text(render(conv))
            continue
        if not valid.is_valid(conv):
            problems = problems + ['fails markdownConversation']
        if problems:
            n_bad += 1
            print(f"  INVALID {name}: {'; '.join(problems)}", file=sys.stderr)
        else:
            n_ok += 1
        (out / f"{name}.md").write_text(render(conv))
    return n_ok, n_bad, n_empty


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--browser-captures', help='dir of <uuid>/ apiConversation capture folders')
    src.add_argument('--bulk-export', help='a bulk-export batch dir whose atomised json/ pieces are rendered')
    ap.add_argument('--out', help='output dir (default: gen/<pipeline>/[<batch>/]markdown)')
    args = ap.parse_args()

    if args.browser_captures:
        # browser captures: same canonical <ordinal>-<slug> ordering (created_at) as the bulk pieces
        apis = [api for d in sorted(p for p in Path(args.browser_captures).iterdir() if p.is_dir())
                if (api := find_api_json(d)) is not None]
        named = [(name, project(api), tree_problems(api['chat_messages']))
                 for _, name, api in ordered(apis)]
        out = Path(args.out) if args.out else REPO / 'gen' / 'markdown' / 'claude'
    else:
        # bulk export: render the pieces atomise_bulk.py wrote, inheriting each piece's name
        batch = Path(args.bulk_export)
        json_dir = REPO / 'gen' / 'chat-exports' / batch.name / 'json'
        if not json_dir.is_dir():
            sys.exit(f"no atomised json/ at {json_dir}; run atomise_bulk.py --bulk-export {batch} first")
        named = ((f.stem, project(c), tree_problems(c['chat_messages']))
                 for f in sorted(json_dir.glob('*.json'))
                 for c in (json.loads(f.read_text()),))
        out = Path(args.out) if args.out else REPO / 'gen' / 'chat-exports' / batch.name / 'markdown'

    n_ok, n_bad, n_empty = write_markdown(named, out)
    print(f"rendered {n_ok} conversations to {out} ({n_bad} invalid, {n_empty} empty)")
    sys.exit(1 if n_bad else 0)


if __name__ == '__main__':
    main()
