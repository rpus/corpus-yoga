#!/usr/bin/env python
"""
project_markdown.py — Render conversations to flat markdown, one <name>.md per conversation,
from either source:
  browser-capture  ext/browser-captures/claude/<uuid>/apiConversation.json   (named by title-slug)
  bulk-export      gen/chat-exports/<batch>/json/<name>.json                  (the atomised pieces;
                                                                               run atomise_bulk.py first)

The markdown CLI over the shared primitives in src/main/markdown_projection.py. Markdown is
validated against rsc/schema/browser-captures/markdownConversation/v1.json. Splitting the bulk
array into the per-conversation json/ pieces is atomise_bulk.py's job; this tool only consumes
them, so json/<name>.json and markdown/<name>.md share a name. Nothing is skipped:
invalid/degenerate conversations are rendered honestly and flagged.

Usage (output defaults per pipeline/batch; --out overrides):
  src/run_python_script.sh src/main/model/project_markdown.py \
    --browser-captures ext/browser-captures/claude              # -> gen/browser-captures/markdown/
  src/run_python_script.sh src/main/model/project_markdown.py \
    --bulk-export ext/chat-exports/<batch>                       # -> gen/chat-exports/<batch>/markdown/
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import REPO, project, assign_name, find_api_json, render, md_validator


def write_markdown(named_convs, out_dir):
    """Render (name, lean-conv) pairs to <name>.md in out_dir, each validated against
    markdownConversation. Nothing skipped -- invalid/degenerate convs are written and flagged.
    Returns (n_ok, n_bad)."""
    valid = md_validator()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_ok = n_bad = 0
    for name, conv in named_convs:
        if valid.is_valid(conv):
            n_ok += 1
        else:
            n_bad += 1
            print(f"  INVALID markdown {name}", file=sys.stderr)
        (out / f"{name}.md").write_text(render(conv))
    return n_ok, n_bad


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--browser-captures', help='dir of <uuid>/ apiConversation capture folders')
    src.add_argument('--bulk-export', help='a bulk-export batch dir whose atomised json/ pieces are rendered')
    ap.add_argument('--out', help='output dir (default: gen/<pipeline>/[<batch>/]markdown)')
    args = ap.parse_args()

    if args.browser_captures:
        # browser captures: name each by its title-slug (uuid-disambiguated)
        seen, named = set(), []
        for d in sorted(p for p in Path(args.browser_captures).iterdir() if p.is_dir()):
            api = find_api_json(d)
            if api is None:
                continue
            lean = project(api)
            named.append((assign_name(lean['title'], api['uuid'], seen), lean))
        out = Path(args.out) if args.out else REPO / 'gen' / 'browser-captures' / 'markdown'
    else:
        # bulk export: render the pieces atomise_bulk.py wrote, inheriting each piece's name
        batch = Path(args.bulk_export)
        json_dir = REPO / 'gen' / 'chat-exports' / batch.name / 'json'
        if not json_dir.is_dir():
            sys.exit(f"no atomised json/ at {json_dir}; run atomise_bulk.py --bulk-export {batch} first")
        named = ((f.stem, project(json.loads(f.read_text()))) for f in sorted(json_dir.glob('*.json')))
        out = Path(args.out) if args.out else REPO / 'gen' / 'chat-exports' / batch.name / 'markdown'

    n_ok, n_bad = write_markdown(named, out)
    print(f"rendered {n_ok} conversations to {out} ({n_bad} invalid)")


if __name__ == '__main__':
    main()
