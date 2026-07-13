#!/usr/bin/env python
"""
atomise_bulk.py — Split a bulk export's conversations.json (one big array) into verbatim
per-conversation JSON files, one per Conversation, each validated against the Conversation
definition in the latest conversations schema (inner-ref; no separate/duplicated schema).

  input/claude/chat/bulk-export/<batch>/conversations.json  -->  cache/chat-exports/<batch>/json/<ordinal>-<slug>.json

This is the ONLY reader of the 24 MB array. Everything downstream consumes the per-conversation
pieces instead: project_markdown.py renders them to markdown/, compare_sources.py cross-checks
them against the live captures. Nothing is skipped -- invalid conversations are written and
flagged, so failures show up in the filesystem. Names come from markdown_projection.ordered() --
the one canonical "<ordinal>-<slug>" (created_at order, 1-based, zero-padded) shared with the
timeline and the markdown/ files -- so json/<name>.json, markdown/<name>.md, and timeline
conversation <ordinal> all correspond, and a plain filesystem sort is conversation order.

Usage (output defaults per batch; --out overrides):
  src/run_python_script.sh src/main/chat-exports/atomise_bulk.py \
    --bulk-export input/claude/chat/bulk-export/<batch>            # -> cache/chat-exports/<batch>/json/
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/main/ on the path
from markdown_projection import REPO, ordered
CONV_SCHEMAS = REPO / 'rsc' / 'schema' / 'chat-exports' / 'conversations'


def conversation_validator():
    """Validate a single Conversation against the latest conversations schema's Conversation
    definition -- inner-ref (root array -> single), no separate/duplicated schema."""
    import jsonschema
    latest = max(CONV_SCHEMAS.glob('v*.json'), key=lambda p: int(re.findall(r'\d+', p.stem)[0]))
    schema = {**json.loads(latest.read_text()), 'allOf': [{'$ref': '#/definitions/Conversation'}]}
    return jsonschema.Draft4Validator(schema)


def atomise(batch_dir, out_dir):
    """Split <batch_dir>/conversations.json into verbatim per-conversation files in out_dir."""
    conv_valid = conversation_validator()
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)  # renumbering renames files; wipe so no old-naming pieces linger
    out_dir.mkdir(parents=True, exist_ok=True)
    convs = json.loads((Path(batch_dir) / 'conversations.json').read_text())
    bad = empty = 0
    detail = []  # per-piece detail is a file, not a log spray: an old export not
    # matching the LATEST definition is ordinary schema history, one count's worth
    for idx, name, raw in ordered(convs):  # canonical <ordinal>-<slug>, created_at order
        (out_dir / f"{name}.json").write_text(json.dumps(raw, indent=2, ensure_ascii=False) + '\n')
        if idx is None:
            empty += 1  # content-free stub, written under its quarantine name; not "invalid"
            continue
        if not conv_valid.is_valid(raw):
            bad += 1
            err = sorted(conv_valid.iter_errors(raw), key=lambda e: list(e.path))[0]
            loc = '/'.join(str(p) for p in err.path)
            detail.append(f"{name} @ {loc} ({err.validator})")
    if detail:
        (out_dir / 'invalid.log').write_text('\n'.join(detail) + '\n')
    print(f"atomised {len(convs)} conversations to {out_dir} "
          f"({bad} do not match the latest Conversation definition"
          + (" — detail: json/invalid.log" if bad else "")
          + f", {empty} empty)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bulk-export', required=True, help='a bulk-export batch dir (containing conversations.json)')
    ap.add_argument('--out', help='output dir (default: cache/chat-exports/<batch>/json)')
    args = ap.parse_args()
    batch = Path(args.bulk_export)
    out = Path(args.out) if args.out else REPO / 'cache' / 'chat-exports' / batch.name / 'json'
    atomise(batch, out)


if __name__ == '__main__':
    main()
