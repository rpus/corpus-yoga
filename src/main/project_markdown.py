"""
project_markdown.py — Render conversations to flat markdown, one <name>.md per conversation,
from either source:
  browser-capture  cache/pipeline/claude/chat/API-capture/<uuid>/                    (named <ordinal>-<slug>;
                                                                               the run's renderings,
                                                                               src/main/browser/claude/render.py)
  bulk-export      cache/pipeline/claude/chat/bulk-export/<batch>/rendered/<name>.md               (the run's renderings
                                                                               of the atomised pieces,
                                                                               src/main/export/render.py)

The markdown CLI over the shared primitives in src/main/markdown_projection.py. Markdown is
validated against the markdownConversation family's latest version (rsc/schema/browser/markdownConversation). Splitting the bulk
array into the per-conversation json/ pieces is atomise_bulk.py's job, and rendering each the
run's; this tool only dresses and places the renderings, so json/<name>.json, rendered/<name>.md
and markdown/<name>.md share a name. Nothing is skipped: invalid/degenerate conversations are
written honestly and flagged.

Usage (output defaults per pipeline/batch; --out overrides):
  src/run_python_script.sh src/main/project_markdown.py \
    --api-capture data/input/claude/chat/API-capture              # -> data/output/markdown/claude/chat/conversations/
  src/run_python_script.sh src/main/project_markdown.py \
    --bulk-export data/input/claude/chat/bulk-export/<batch>                       # -> cache/pipeline/claude/chat/bulk-export/<batch>/markdown/
"""
import argparse
import json
import sys
from pathlib import Path
import tier  # the tiers, one home (issues/702)
import corpus
from markdown_projection import (FACTS, RENDERED, RENDERINGS, ordered, find_api_json, compose,
                                 deposit, conv_id)
from vintage import export_time  # the one export-ordering authority

REPO_ROOT = tier.REPO



def _newest_batch_json():
    """The newest ATOMISED export's json/ dir (by export_time, the one ordering
    authority), or None where no batch has been atomised."""
    cache = corpus.store_cache('export')
    atomised = [d for d in cache.glob('data-*') if (d / 'json').is_dir()]
    if not atomised:
        return None
    import datetime
    floor = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    return max(atomised, key=lambda d: export_time(d.name) or floor) / 'json'


def _msg_index(convs):
    """{conversation uuid: {message uuid: created_at}} — the atoms each corpus holds,
    for the per-conversation currency cross-check."""
    return {c['uuid']: {m['uuid']: m['created_at'] for m in c['chat_messages']}
            for c in convs}


def _currency(mine, other, label):
    """One line of KNOWN staleness for the frontmatter, from message-uuid sets (the
    calculus's atom-subset — the same per-conversation comparison the export
    run's compare_captures step reports corpus-wide). `other` is None when the conversation is absent
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


def _frontmatter(source, record, other_index, other_name, other_label):
    """The provenance dressing for one rendered file (see markdownConversation v3's
    CHANGELOG: dressing, not schema), from the conversation's facts: facts only — the
    file's outbound LINKS live as named bullets in the rendered body (render()'s source
    list), clickable in any markdown renderer. Every value derives from the local corpora —
    no wall-clock — so regeneration is a no-op until data changes (L1)."""
    return {
        'source': source,
        'uuid': record['uuid'],
        'human': record['human'],          # the turn count's one home, by role (issues/1001)
        'assistant': record['assistant'],
        'last_activity': (record.get('updated_at') or '')[:19] + 'Z',
        'cross_checked_against': other_name or 'none',
        'currency': ('unchecked' if other_index is None
                     else _currency(record['messages'], other_index.get(record['uuid']), other_label)),
    }


def _rendered(captures):
    """Each capture's rendering and facts, as the run wrote them at its cache address
    (src/main/browser/claude/render.py); the collate stops, naming them, where any is
    missing, since depositing without one would prune its conversation's file."""
    held, missing = [], []
    for d in sorted(p for p in Path(captures).iterdir() if p.is_dir()):
        cache = tier.cache_of(d)
        if (cache / RENDERED).is_file() and (cache / FACTS).is_file():
            held.append((json.loads((cache / FACTS).read_text()), (cache / RENDERED).read_text()))
        elif find_api_json(d) is not None:
            missing.append(d.name)
    if missing:
        sys.exit(f"no rendering at the cache address of {len(missing)} capture(s) - {', '.join(missing)}; "
                 f"corpus-yoga pipeline run renders each")
    return held


def write_markdown(named_convs, out_dir):
    """Compose (name, rendered body, problems, frontmatter, summaries-link) tuples into
    <name>.md in out_dir (the frontmatter is dressing, outside the schema; the summaries
    link becomes a named bullet in the body's source list). Nothing skipped --
    invalid/degenerate convs are written and flagged, with WHY: an unwalkable tree
    projects to a fragment that would otherwise still validate. Reconciles rather than wiping (reconcile_dir):
    unchanged renders keep their mtime, renamed/removed convs' files are the orphans it
    prunes. Returns (n_ok, n_bad, n_empty)."""
    n_ok = n_bad = n_empty = 0
    files = {}
    for name, body, problems, fm, slink in named_convs:
        if name.startswith('empty-'):
            # ordered() already classified this stub and named it so (the atomised piece
            # stems carry the name to the bulk path) — one authority, no re-deciding here.
            n_empty += 1
        else:
            if problems:
                n_bad += 1
                print(f"  INVALID {name}: {'; '.join(problems)}", file=sys.stderr)
            else:
                n_ok += 1
        files[f"{name}.md"] = compose(body, fm, slink)
    deposit(out_dir, files, f'  markdown: {len(files)} conversation(s)', identity=conv_id,
            because='its conversation left the source', file=sys.stderr)
    return n_ok, n_bad, n_empty


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--api-capture', help='dir of <uuid>/ apiConversation capture folders')
    src.add_argument('--bulk-export', help='a bulk-export batch dir whose atomised json/ pieces are rendered')
    ap.add_argument('--out', help='output dir (default: data/output/markdown/claude/chat/conversations for captures, the batch cache\'s markdown/ for an export)')
    args = ap.parse_args()

    if args.api_capture:
        # browser captures: each rendered by the run, named here by the same canonical
        # <ordinal>-<slug> ordering (created_at) as the bulk pieces. Provenance cross-checks
        # against the newest atomised export batch (offline, local — staleness vs claude.ai
        # live stays audit --live's job).
        held = _rendered(args.api_capture)
        rendered = {record['uuid']: body for record, body in held}
        other = _newest_batch_json()
        other_index = (_msg_index(json.loads(f.read_text()) for f in sorted(other.glob('*.json')))
                       if other else None)
        other_name = other.parent.name if other else None
        named = [(name, rendered[record['uuid']], record['problems'],
                  _frontmatter('browser-capture', record, other_index, other_name, 'export'),
                  f'../summaries/{name}/index.md')
                 for _, name, record in ordered(record for record, _ in held)]
        out = Path(args.out) if args.out else tier.DATA / 'output' / 'markdown' / 'claude' / 'chat' / 'conversations'
    else:
        # bulk export: the run's renderings of the pieces atomise_bulk.py wrote, each under
        # its piece's name (src/main/export/render.py). Provenance cross-checks the other
        # way: against the capture corpus, when present.
        batch = Path(args.bulk_export)
        cache = tier.cache_of(batch)
        if not (cache / FACTS).is_file():
            sys.exit(f"no rendering at the cache address of {batch.name}; corpus-yoga pipeline run renders it")
        record = json.loads((cache / FACTS).read_text())
        captures = tier.DATA / 'input' / 'claude' / 'chat' / 'API-capture'
        cap_apis = ([api for d in sorted(p for p in captures.iterdir() if p.is_dir())
                     if (api := find_api_json(d)) is not None] if captures.is_dir() else None)
        other_index = _msg_index(cap_apis) if cap_apis else None
        other_name = 'data/input/claude/chat/API-capture' if cap_apis else None
        # no summaries link here: cache/ stems renumber per batch, so a relative
        # link into data/output/'s stem-named folders would dangle
        named = ((name, (cache / RENDERINGS / f'{name}.md').read_text(), held['problems'],
                  _frontmatter('bulk-export', held, other_index, other_name, 'capture'),
                  None)
                 for name, held in sorted(record.items()))
        out = Path(args.out) if args.out else cache / 'markdown'

    n_ok, n_bad, n_empty = write_markdown(named, out)
    print(f"rendered {n_ok} conversations to {out} ({n_bad} invalid, {n_empty} empty)")
    sys.exit(1 if n_bad else 0)


if __name__ == '__main__':
    main()
