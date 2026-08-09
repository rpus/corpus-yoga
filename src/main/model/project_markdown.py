#!/usr/bin/env python
"""
project_markdown.py — Render conversations to flat markdown, one <name>.md per conversation,
from either source:
  browser-capture  data/input/claude/chat/browser-API/<uuid>/apiConversation.json   (named <ordinal>-<slug>)
  bulk-export      tmp/cache/chat-exports/<batch>/json/<name>.json                  (the atomised pieces;
                                                                               run atomise_bulk.py first)

The markdown CLI over the shared primitives in src/main/markdown_projection.py. Markdown is
validated against rsc/schema/browser-captures/markdownConversation/v3.json. Splitting the bulk
array into the per-conversation json/ pieces is atomise_bulk.py's job; this tool only consumes
them, so json/<name>.json and markdown/<name>.md share a name. Nothing is skipped:
invalid/degenerate conversations are rendered honestly and flagged.

Usage (output defaults per pipeline/batch; --out overrides):
  src/run_python_script.sh src/main/model/project_markdown.py \
    --browser-api data/input/claude/chat/browser-API              # -> data/output/markdown/claude/chat/conversations/
  src/run_python_script.sh src/main/model/project_markdown.py \
    --bulk-export data/input/claude/chat/bulk-export/<batch>                       # -> tmp/cache/chat-exports/<batch>/markdown/
"""
import argparse
import json
import sys
from pathlib import Path

SELF = 'src/main/model/project_markdown.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO_ROOT = _root[0]
sys.path.insert(0, str(REPO_ROOT / 'src' / 'main'))  # src/main/ on the path
from markdown_projection import (REPO, project, ordered, find_api_json, render,
                                 md_validator, tree_problems, deposit, conv_id)

sys.path.insert(0, str(REPO_ROOT / 'src' / 'main' / 'pipeline' / 'chat-exports'))
from supersede import batch_time  # noqa: E402 — the one batch-ordering authority


def _newest_batch_json():
    """The newest ATOMISED batch's json/ dir (by batch_time, the one ordering
    authority), or None where no batch has been atomised."""
    cache = REPO / 'tmp' / 'cache' / 'chat-exports'
    atomised = [d for d in cache.glob('data-*') if (d / 'json').is_dir()]
    if not atomised:
        return None
    import datetime
    floor = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    return max(atomised, key=lambda d: batch_time(d.name) or floor) / 'json'


def _msg_index(convs):
    """{conversation uuid: {message uuid: created_at}} — the atoms each corpus holds,
    for the per-conversation currency cross-check."""
    return {c['uuid']: {m['uuid']: m['created_at'] for m in c['chat_messages']}
            for c in convs}


def _currency(mine, other, label):
    """One line of KNOWN staleness for the frontmatter, from message-uuid sets (the
    calculus's atom-subset — the same per-conversation comparison supersede
    --captures reports corpus-wide). `other` is None when the conversation is absent
    from the other corpus; `label` names that corpus."""
    if other is None:
        return f'no-{label}'
    m, o = set(mine), set(other)
    if m == o:
        return 'in-sync'
    if o < m:
        return f'ahead-of-{label}: +{len(m - o)} messages here'
    if m < o:
        newest = max(other[u] for u in o - m)
        return f'stale: {label} holds {len(o - m)} newer messages (through {newest[:19]}Z)'
    return f'anomaly: unique messages both here and in the {label}'


def _frontmatter(source, conv, lean, other_index, other_name, other_label):
    """The provenance dressing for one rendered file (see markdownConversation v3's
    CHANGELOG: dressing, not schema): facts only — the file's outbound LINKS live as
    named bullets in the rendered body (render()'s source list), clickable in any
    markdown renderer. Every value derives from the local corpora — no wall-clock —
    so regeneration is a no-op until data changes (L1)."""
    mine = {m['uuid']: m['created_at'] for m in conv['chat_messages']}
    return {
        'source': source,
        'uuid': conv['uuid'],
        'turns': len(lean['messages']),
        'last_activity': (conv.get('updated_at') or '')[:19] + 'Z',
        'cross_checked_against': other_name or 'none',
        'currency': ('unchecked' if other_index is None
                     else _currency(mine, other_index.get(conv['uuid']), other_label)),
    }


def write_markdown(named_convs, out_dir):
    """Render (name, lean-conv, tree-problems, frontmatter, summaries-link) tuples to
    <name>.md in out_dir, each lean conv validated against markdownConversation (the
    frontmatter is dressing, outside the schema; the summaries link becomes a named
    bullet in the body's source list). Nothing skipped -- invalid/degenerate convs are
    written and flagged, with WHY: an unwalkable tree projects to a fragment that
    would otherwise still validate. Reconciles rather than wiping (reconcile_dir):
    unchanged renders keep their mtime, renamed/removed convs' files are the orphans it
    prunes. Returns (n_ok, n_bad, n_empty)."""
    valid = md_validator()
    n_ok = n_bad = n_empty = 0
    files = {}
    for name, conv, problems, fm, slink in named_convs:
        if name.startswith('empty-'):
            # ordered() already classified this stub and named it so (the atomised piece
            # stems carry the name to the bulk path) — one authority, no re-deciding here.
            n_empty += 1
        else:
            if not valid.is_valid(conv):
                problems = problems + ['fails markdownConversation']
            if problems:
                n_bad += 1
                print(f"  INVALID {name}: {'; '.join(problems)}", file=sys.stderr)
            else:
                n_ok += 1
        files[f"{name}.md"] = render(conv, frontmatter=fm, summaries_link=slink)
    deposit(out_dir, files, f'  markdown: {len(files)} conversation(s)', identity=conv_id,
            because='its conversation left the source', file=sys.stderr)
    return n_ok, n_bad, n_empty


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--browser-api', help='dir of <uuid>/ apiConversation capture folders')
    src.add_argument('--bulk-export', help='a bulk-export batch dir whose atomised json/ pieces are rendered')
    ap.add_argument('--out', help='output dir (default: tmp/cache/<pipeline>/[<batch>/]markdown)')
    args = ap.parse_args()

    if args.browser_api:
        # browser captures: same canonical <ordinal>-<slug> ordering (created_at) as the bulk
        # pieces. Provenance cross-checks against the newest atomised export batch (offline,
        # local — staleness vs claude.ai live stays audit_captures --live's job).
        apis = [api for d in sorted(p for p in Path(args.browser_api).iterdir() if p.is_dir())
                if (api := find_api_json(d)) is not None]
        other = _newest_batch_json()
        other_index = (_msg_index(json.loads(f.read_text()) for f in sorted(other.glob('*.json')))
                       if other else None)
        other_name = other.parent.name if other else None
        named = [(name, lean, tree_problems(api['chat_messages']),
                  _frontmatter('browser-capture', api, lean, other_index, other_name, 'export'),
                  f'../summaries/{name}/index.md')
                 for _, name, api in ordered(apis)
                 for lean in (project(api),)]
        out = Path(args.out) if args.out else REPO / 'data' / 'output' / 'markdown' / 'claude' / 'chat' / 'conversations'
    else:
        # bulk export: render the pieces atomise_bulk.py wrote, inheriting each piece's name.
        # Provenance cross-checks the other way: against the capture corpus, when present.
        batch = Path(args.bulk_export)
        json_dir = REPO / 'tmp' / 'cache' / 'chat-exports' / batch.name / 'json'
        if not json_dir.is_dir():
            sys.exit(f"no atomised json/ at {json_dir}; run atomise_bulk.py --bulk-export {batch} first")
        captures = REPO / 'data' / 'input' / 'claude' / 'chat' / 'browser-API'
        cap_apis = ([api for d in sorted(p for p in captures.iterdir() if p.is_dir())
                     if (api := find_api_json(d)) is not None] if captures.is_dir() else None)
        other_index = _msg_index(cap_apis) if cap_apis else None
        other_name = 'data/input/claude/chat/browser-API' if cap_apis else None
        # no summaries link here: tmp/cache/ stems renumber per batch, so a relative
        # link into data/output/'s stem-named folders would dangle
        named = ((f.stem, lean, tree_problems(c['chat_messages']),
                  _frontmatter('bulk-export', c, lean, other_index, other_name, 'capture'),
                  None)
                 for f in sorted(json_dir.glob('*.json'))
                 for c in (json.loads(f.read_text()),)
                 for lean in (project(c),))
        out = Path(args.out) if args.out else REPO / 'tmp' / 'cache' / 'chat-exports' / batch.name / 'markdown'

    n_ok, n_bad, n_empty = write_markdown(named, out)
    print(f"rendered {n_ok} conversations to {out} ({n_bad} invalid, {n_empty} empty)")
    sys.exit(1 if n_bad else 0)


if __name__ == '__main__':
    main()
